__Reports bot__ maintains reports and other useful things for
[WikiProjects](https://en.wikipedia.org/wiki/Wikipedia:WikiProject).

# Setup

First, clone the bot:

    git clone git@github.com:harej/reports_bot.git
    cd reports_bot

Python 3.4+ is required. You should set up and activate a
[virtual environment](https://www.python.org/dev/peps/pep-0405/) in the `venv`
directory, though this is not required. The following workaround may be
necessary on Debian systems:

    python3 -m venv --without-pip venv
    source venv/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python

Next, install these dependencies:

    pip install pywikibot requests PyYAML PyMySQL mwparserfromhell \
    mediawiki-utilities numpy scikit-learn

If you set up a virtualenv, run the following command to ensure the bot's task
runner always uses it:

    sed -e "1s|.*|#! $PWD/venv/bin/python|" -i "" ./run

## Unprivileged user

Depending on your setup, you may wish to create a separate, unprivileged user
for the bot. The recommended method is:

    sudo adduser --system --home /path/to/reportsbot reportsbot

If so, make sure to create the bot's `config` and `logs` directories with the
appropriate ownership:

    mkdir config logs && sudo chown reportsbot config logs

## Database

Reports bot uses a MySQL database to store its on-wiki config, the WikiProject
page indices, and some other information. Create this database using the schema
described in `schema.sql`. You may change the database name—for example, on
Labs, it should probably be something like `sXXXXX__wpx`.

## Config

The bot requires a `config/config.yml` file for itself and
`config/user-config.py` file for Pywikibot. The easiest way to create these
is with the configuration assistant:

    ./run configure

(As described below, you should use `sudo ./run configure` if the bot is
running under an unprivileged user.)

Afterwards, you may edit these files manually whenever necessary.

# Usage

Reports bot's standard tasks are located in the `tasks/` directory. A `./run`
script is provided to make things simple, assuming you've followed the standard
setup procedure above.

To run a task located at `tasks/foobar.py`:

    ./run foobar

For a full description of the command-line interface:

    ./run --help

If you're using a separate user for the bot, be aware that the `./run` script
tries to ensure that it is running under the account that owns the `config`
directory. You can run jobs from `reportsbot`'s crontab using the plain `./run`
syntax, but manual jobs under your own account should be initiated with
`sudo ./run`.

If you prefer to use `reportsbot` as a regular Python package and execute task
files at arbitrary locations, you can use this syntax, which supports the same
arguments as `./run`:

    python3 -m reportsbot.cli full/path/to/task.py
    python3 -m reportsbot.cli --help

# Tasks

A number of tasks are provided. Advice on developing your own is given at the
end of this section.

* `update_members`: Updates WikiProject membership lists based on
  WikiProjectCard transclusions.
* `update_project_index`: Updates the index of articles associated with each
  project.

## Developing

To create new tasks, you can follow the skeleton in `example.py`. Important
things to keep in mind:

* The name of the task class doesn't matter (the bot searches by filename), but
  it should be descriptive.
* The `run` method is the only method called by the task runner, other than
  `__init__`, which should only do inexpensive setup if you override it.
* There should only be one Task subclass per module. `__all__` is used to
  identify which class to run in case multiple exist in the module namespace,
  like if you import other Task subclasses to use their methods.

The task has access to two important attributes:

* `self._bot` is the Bot instance, which provides the following functionality:
    * `self._bot.site`: the Pywikibot site instance
    * `self._bot.wikidb`: a database connection to the wiki replica
    * `self._bot.localdb`: a connection to the bot's local database
  Some methods are available for working with WikiProjects in a structured
  manner. See the `reportsbot.bot.Bot` class documentation for details.
* `self._logger` is the
  [Logger](https://docs.python.org/3/library/logging.html#logging.Logger.debug)
  instance that you should use for all log messages.
