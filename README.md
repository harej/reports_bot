# Setup

Python 3 is required. You should set up and activate a
[virtual environment](https://www.python.org/dev/peps/pep-0405/) in the `venv`
directory. The following workaround may be necessary on Debian systems:

    python3 -m venv --without-pip venv
    source venv/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python

Next, install these dependencies:

    pip install pywikibot requests PyMySQL mwparserfromhell \
    mediawiki-utilities numpy scikit-learn

You'll need to create a `user-config.py` file for Pywikibot.
