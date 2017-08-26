# Contributing to Plumbum


## General comments

Pull requests welcome! Please make sure you add tests (in an easy `pytest` format) to the tests folder for your fix or features. Make sure you add documentation covering a new feature.

## Adding a language

Plumbum.cli prints various messages for the user. These can be localized into your local language; pull requests adding languages are welcome.

To add a language, copy the file `plumbum/cli/i18n/messages.pot` to `plumbum/cli/i18n/locale/<lang>/LC_MESSAGES/<lang>.po`, and add your language. 


See `gettext: PMOTW3 <https://pymotw.com/3/gettext/>`_ for more info.
