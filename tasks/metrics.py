# -*- coding: utf-8 -*-

from datetime import datetime
import re

from reportsbot.task import Task
from reportsbot.util import to_sql_format, split_full_title, join_full_title

__all__ = ["Metrics"]

class Metrics(Task):
    """Updates monthly metrics on the number of articles in a project."""

    @staticmethod
    def _get_months(start_month):
        """Return a list of month strings from the given start until now."""
        try:
            start = datetime.strptime(start_month, "%B %Y")
        except ValueError:
            start = datetime.strptime(start_month, "%b %Y")

        end = datetime.utcnow()
        end = datetime(end.year, end.month, 1)

        if start > end:
            raise ValueError(start_month)

        months = [start]
        while months[-1] < end:
            prev = months[-1]
            if prev.month == 12:
                months.append(datetime(prev.year + 1, 1, 1))
            else:
                months.append(datetime(prev.year, prev.month + 1, 1))

        return months

    def _fetch_articles_by_index(self, project):
        """Return a list of articles in the project, using the SQL index."""
        self._logger.debug("Using project index for scope")
        pages = project.get_members(namespaces=0, redirect=False)
        return [(page.ns, page.title) for page in pages]

    def _fetch_articles_by_wikidata(self, query):
        """Return a set of articles in the project, using a Wikidata query."""
        self._logger.debug("Using Wikidata for scope")
        query = "({}) AND LINK[{}]".format(query, self._bot.wikiid)
        items = self._bot.wikidata.query(query)
        titles = self._bot.wikidata.get_linked_pages(self._bot.wikiid, items)
        return {split_full_title(self._bot.site, title) for title in titles}

    def _fetch_articles_by_categories(self, cats):
        """Return a set of articles in the project, using a list of cats."""
        self._logger.debug("Using categories for scope")

        query = """SELECT page_namespace, page_title
        FROM categorylinks
        JOIN page ON page_id = cl_from
        WHERE cl_to IN ({})
        AND page_namespace IN (0, 14) AND page_is_redirect = 0"""

        pages = set()
        cats = [to_sql_format(cat) for cat in cats]
        processed = []

        with self._bot.wikidb as cursor:
            while cats:
                processed.extend(cats)
                cursor.execute(query.format(", ".join("?" * len(cats))), cats)
                results = [(ns, title.decode("utf8"))
                           for (ns, title) in cursor.fetchall()]

                pages |= {(ns, title) for (ns, title) in results if ns == 0}
                cats = [title for (ns, title) in results
                        if ns == 14 and title not in processed]

        return pages

    def _fetch_articles(self, project):
        """Return a list of articles in the project."""
        config = project.config["metrics"]
        cats = config.get("categories")
        wdq = config.get("wikidata_query")

        if not cats and not wdq:
            return self._fetch_articles_by_index(project)

        articles = set()
        if cats:
            articles |= self._fetch_articles_by_categories(cats)
        if wdq:
            articles |= self._fetch_articles_by_wikidata(wdq)
        return list(articles)

    def _lookup_pages(self, pages):
        """Given some pages, return a list of them and their creation dates."""
        query = """SELECT page_namespace, page_title, MIN(rev_timestamp)
        FROM revision
        JOIN page ON rev_page = page_id
        WHERE ({})
        GROUP BY page_id"""
        clause = "(page_namespace = ? AND page_title = ?)"

        chunksize = 10000
        results = []

        with self._bot.wikidb as cursor:
            for start in range(0, len(pages), chunksize):
                if start != 0:
                    self._logger.debug("Done: %s/%s", start, len(pages))

                chunk = pages[start:start+chunksize]
                params = " OR ".join([clause] * len(chunk))
                args = [arg for page in chunk for arg in page]

                cursor.execute(query.format(params), args)
                chunkdata = cursor.fetchall()
                results.extend([(ns, title.decode("utf8"), ts.decode("utf8"))
                                for (ns, title, ts) in chunkdata])

        return results

    def _bucket_articles(self, articles, buckets):
        """Place each article inside a month bucket."""
        self._logger.debug("Bucketing articles")

        pages = self._lookup_pages(articles)
        for (ns, title, timestamp) in pages:
            creation = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            month = datetime(creation.year, creation.month, 1)
            if month in buckets:
                buckets[month].append((ns, title))

    def _check_for_redlinks(self, titles):
        """Given a list of article titles, return those which don't exist."""
        if not titles:
            return []

        self._logger.debug("Checking %s possible redlinks", len(titles))

        query = "SELECT page_namespace, page_title FROM page WHERE ({})"
        clause = "(page_namespace = ? AND page_title = ?)"

        with self._bot.wikidb as cursor:
            params = " OR ".join([clause] * len(titles))
            args = [arg for title in titles
                    for arg in split_full_title(self._bot.site, title)]

            cursor.execute(query.format(params), args)
            results = cursor.fetchall()

        valid = {join_full_title(self._bot.site, ns, title.decode("utf8"))
                 for (ns, title) in results}
        return list(set(titles) - valid)

    def _list_item_for_title(self, title):
        """Return a list item string for the given title."""
        if ":" in title:
            ns_name, base = title.split(":", 1)
            ns_dict = self._bot.site.namespaces
            if ns_name in ns_dict:
                title = ns_dict[ns_name].custom_prefix + base
        return "# [[{}]]".format(title)

    def _build_page_list(self, articles, oldlist):
        """Return a metrics subpage's new article list."""
        titles = [join_full_title(self._bot.site, ns, title)
                  for (ns, title) in articles]
        possible_redlinks = []

        # Preliminary list of plain bot-generated entries:
        entries = {title: self._list_item_for_title(title) for title in titles}

        # Merge in current (user-generated) entries:
        for line in oldlist.splitlines():
            link = re.search(r"\[\[:?(.*?)(\]\]|\|)", line)
            if not link:
                continue

            title = link.group(1).strip()
            if title not in entries:
                possible_redlinks.append(title)
            entries[title] = line

        for title in self._check_for_redlinks(possible_redlinks):
            del entries[title]

        # Join list of entries' values, sorted by the corresponding keys:
        pagelist = "\n".join(val for (key, val) in
                             sorted(entries.items(), key=lambda item: item[0]))

        # Exclude commented-out lines in the count:
        count = sum(1 for val in entries.values() if val.startswith("#"))
        return pagelist, count

    def _build_page_text(self, month, articles, oldtext, template):
        """Return a metrics subpage's new content."""
        self._logger.debug("Updating month: %s (%s articles)",
                           month.strftime("%B %Y"), len(articles))

        comment = "<!-- Reports bot variable: {} {} -->"
        wrap = lambda key, body: (
            comment.format("start", key) + body + comment.format("end", key))

        oldlist = re.search(wrap("list", r"(.*?)"), oldtext, re.S)
        pagelist, count = self._build_page_list(
            articles, oldlist.group(1).strip() if oldlist else "")

        replacements = {
            "list": wrap("list", "\n" + pagelist + "\n"),
            "articlecount": wrap("count", str(count)),
            "date": month.strftime("%B %Y"),
            "month": month.strftime("%B"),
            "year": month.strftime("%Y")
        }

        if oldtext:
            newtext = oldtext
            newtext = re.sub(wrap("list", r"(.*?)"), replacements["list"],
                             newtext, flags=re.S)
            newtext = re.sub(wrap("count", r"(.*?)"),
                             replacements["articlecount"], newtext, flags=re.S)
        else:
            newtext = template
            for key, val in replacements.items():
                newtext = newtext.replace("{{{" + key + "}}}", val)

        return newtext

    def _create_metrics_page(self, project, title):
        """Create a missing base metrics page for the given project."""
        self._logger.warn("Creating missing metrics page for %s", project.name)

        text = """{{Archive box|box-width=10em|
{{#invoke:WikiProject metrics|list|%(start)s}}
}}

{{#invoke:WikiProject metrics|chart|%(start)s}}

<noinclude>
{{#invoke:WikiProject metrics|recent|30em}}
<noinclude>"""
        text = text % {"start": project.config["metrics"]["start_month"]}

        page = self._bot.get_page(title)
        page.text = text
        page.save("Creating metrics page", minor=False)

    def _create_template(self, project, title):
        """Create a missing template for the given project."""
        self._logger.warn("Creating missing template for %s", project.name)

        text = """{{#ifeq:{{#time:F Y}}|{{SUBPAGENAME}}||{{archive}}}}
{{main|%(base)s}}

<!-- You don't need to update the number below! It will be updated \
automatically. -->
<section begin="count"/>{{{articlecount}}}<section end="count"/> articles

<!--
== Instructions ==
You may freely add items to this list, and "annotate" existing ones to add \
things like notes, bold, italics, etc.
To remove an entry, turn the whole line into a comment. If you just delete it \
from the page, the bot may add it back.
The bot keeps this list alphabetized and removes deleted pages.
-->

{{Div col||30em}}
<section begin="list"/>
{{{list}}}
<section end="list"/>
{{Div col end}}"""
        text = text % {"base": title.rsplit("/", 1)[0]}

        page = self._bot.get_page(title)
        page.text = text
        page.save("Creating template", minor=False)
        return text

    def _save_metrics(self, project, months, buckets):
        """Save compiled metrics for the given project."""
        config = project.config["metrics"]
        base_title = config.get("page", project.name + "/Metrics")

        if not self._bot.get_page(base_title).text:
            self._create_metrics_page(project, base_title)

        tmpl_title = base_title + "/Template"
        template = self._bot.get_page(tmpl_title).text
        if not template:
            template = self._create_template(project, tmpl_title)

        tmpl_comment = "<!-- Created from: [[{}]] -->\n".format(tmpl_title)
        template = tmpl_comment + template

        for month in months:
            monthname = month.strftime("%B %Y")
            page = self._bot.get_page(base_title + "/" + monthname)
            page.text = self._build_page_text(month, buckets[month], page.text,
                                              template)
            page.save("Updating monthly metrics", minor=False)

    def _update_metrics(self, project):
        """Update metrics for the given project."""
        self._logger.info("Updating metrics for %s", project.name)

        config = project.config["metrics"]
        if "start_month" not in config:
            self._logger.warn("Project %s missing start_month", project.name)
            return

        start = config["start_month"]
        try:
            months = self._get_months(start)
        except ValueError:
            self._logger.warn("Project %s invalid start_month: %s",
                              project.name, start)
            return
        self._logger.debug("%s months, starting with %s", len(months),
                           months[0].strftime("%B %Y"))

        articles = self._fetch_articles(project)
        self._logger.debug("%s articles in scope", len(articles))

        buckets = {month: [] for month in months}
        self._bucket_articles(articles, buckets)

        self._save_metrics(project, months, buckets)

    def run(self):
        for project in self._bot.get_configured_projects():
            if "metrics" not in project.config:
                continue
            if not project.config["metrics"].get("enabled"):
                continue
            self._update_metrics(project)
