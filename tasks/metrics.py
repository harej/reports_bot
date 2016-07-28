# -*- coding: utf-8 -*-

from datetime import datetime
import re

from reportsbot.task import Task
from reportsbot.util import split_full_title, join_full_title

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

    def _fetch_articles_by_wikidata(self, query):
        """Return a list of articles in the project, using a Wikidata query."""
        self._logger.debug("Using Wikidata for scope")
        query = "({}) AND LINK[{}]".format(query, self._bot.wikiid)
        items = self._bot.wikidata.query(query)
        titles = self._bot.wikidata.get_linked_pages(self._bot.wikiid, items)
        return [split_full_title(self._bot.site, title) for title in titles]

    def _fetch_articles_by_index(self, project):
        """Return a list of articles in the project, using the SQL index."""
        self._logger.debug("Using project index for scope")
        pages = project.get_members(namespaces=0, redirect=False)
        return [(page.ns, page.title) for page in pages]

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

        # Sort the buckets in alphabetical order:
        for month in buckets:
            buckets[month].sort(key=lambda item: item[1])

    def _build_page_list(self, articles, oldlist):
        """Return a metrics subpage's new article list."""
        existing = {}

        for line in oldlist.splitlines():
            link = re.search(r"\[\[(.*?)(\]\]|\|)", line, re.S)
            if not link:
                continue
            existing[link.group(1)] = line

        titles = [join_full_title(self._bot.site, ns, title)
                  for (ns, title) in articles]

        return "\n".join(
            existing[title] if title in existing else "# [[{}]]".format(title)
            for title in titles)

    def _build_page_text(self, month, articles, oldtext, template):
        """Return a metrics subpage's new content."""
        self._logger.debug("Updating month: %s (%s articles)",
                           month.strftime("%B %Y"), len(articles))

        comment = "<!-- Reports bot variable: %s %s -->"
        wrap = lambda key, body: (
            comment.format("start", key) + body + comment.format("end", key))

        oldlist = re.search(wrap("list", r"(.*?)"), oldtext, re.S)
        pagelist = self._build_page_list(
            articles, oldlist.group(1).strip() if oldlist else "")

        replacements = {
            "list": wrap("list", "\n" + pagelist + "\n"),
            "articlecount": wrap("count", str(len(articles))),
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

    def _save_metrics(self, project, months, buckets):
        """Save compiled metrics for the given project."""
        # TODO: if base title doesn't exist, create it

        config = project.config["metrics"]
        base_title = config.get("page", project.name + "/Metrics")

        tmpl_title = base_title + "/Template"
        template = self._bot.get_page(tmpl_title).text
        if template:
            tmpl_comment = "<!-- Created from: [[{}]] -->\n".format(tmpl_title)
            template = tmpl_comment + template
        else:
            self._logger.warn("Project %s missing template", project.name)

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

        wdq = config.get("wikidata_query")
        if wdq:
            articles = self._fetch_articles_by_wikidata(wdq)
        else:
            articles = self._fetch_articles_by_index(project)
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
