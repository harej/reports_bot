[TODO: introduction goes here!]

# Setup

Python 3.4+ is required. You should set up and activate a
[virtual environment](https://www.python.org/dev/peps/pep-0405/) in the `venv`
directory. The following workaround may be necessary on Debian systems:

    python3 -m venv --without-pip venv
    source venv/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python

Next, install these dependencies:

    pip install pywikibot requests PyMySQL mwparserfromhell \
    mediawiki-utilities numpy scikit-learn

You'll need to create a `user-config.py` file for Pywikibot. [TODO: instructions]

# Usage

Reports bot's standard tasks are located in the `tasks/` directory. To run a
task located at `tasks/foobar.py`:

    ./run foobar

For a full description of the command-line interface:

    ./run --help

If you prefer to use `reportsbot` as a regular Python package and execute task
files at arbitrary locations, you can use this command, which supports the same
arguments as `./run`:

    python3 -m reportsbot.cli full/path/to/task.py

# Tasks

[TODO: task list]
