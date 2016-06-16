__Reports bot__ maintains reports and other useful things for
[WikiProjects](https://en.wikipedia.org/wiki/Wikipedia:WikiProject).

# Setup

Python 3.4+ is required. You should set up and activate a
[virtual environment](https://www.python.org/dev/peps/pep-0405/) in the `venv`
directory. The following workaround may be necessary on Debian systems:

    python3 -m venv --without-pip venv
    source venv/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python

Next, install these dependencies:

    pip install pywikibot requests PyYAML PyMySQL mwparserfromhell \
    mediawiki-utilities numpy scikit-learn

## Configuring

Depending on your setup, you may wish to create a separate user for Reports
bot. The recommended method is:

    sudo adduser --system --home /path/to/reportsbot reportsbot

Create a `config` directory and ensure that it is owned by Reports bot's user:

    mkdir config && sudo chown reportsbot config

You'll need to create a `config/config.yml` file for Reports bot and a
`config/user-config.py` file for Pywikibot. Ensure that these are readable by
the bot's user.

[TODO: instructions for both]

[config.yml: read_default_file, remark on unpriv user]

[TODO: setup database]

# Usage

Reports bot's standard tasks are located in the `tasks/` directory. To run a
task located at `tasks/foobar.py`:

    ./run foobar

For a full description of the command-line interface:

    ./run --help

The `./run` script ensures that it is running under the user that owns the
`config` directory, and tries to set its user ID if not. This allows you to add
tasks to `reportsbot`'s crontab as well as run one-off jobs with `sudo ./run`,
while keeping everything clean. If you prefer to use `reportsbot` as a regular
Python package and execute task files at arbitrary locations, you can use this
syntax, which supports the same arguments as `./run`:

    python3 -m reportsbot.cli full/path/to/task.py
    python3 -m reportsbot.cli --help

# Tasks

* `update_members`: Updates WikiProject membership lists based on
  WikiProjectCard transclusions.

[TODO: other tasks]
