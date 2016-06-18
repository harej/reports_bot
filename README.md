__Reports bot__ maintains reports and other useful things for
[WikiProjects](https://en.wikipedia.org/wiki/Wikipedia:WikiProject).

# Setup

First, clone the bot:

    git clone git@github.com:harej/reports_bot.git
    cd reports_bot

Python 3.4+ is required. You should set up and activate a
[virtual environment](https://www.python.org/dev/peps/pep-0405/) in the `venv`
directory. The following workaround may be necessary on Debian systems:

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

## Config

You'll need to create a `config/config.yml` file for Reports bot and a
`config/user-config.py` file for Pywikibot. Ensure that these are readable by
the bot's user.

[TODO: instructions for both]

[config.yml: read_default_file, remark on unpriv user]

## Database

Create a database from `schema.sql`.

[TODO: setup database]

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

* `update_members`: Updates WikiProject membership lists based on
  WikiProjectCard transclusions.

[TODO: other tasks]
