Contributing to Plumbum
=======================

General comments
----------------

Pull requests welcome! Please make sure you add tests (in an easy ``pytest`` format) to the tests folder for your fix or features. Make sure you add documentation covering a new feature.

Adding a language
-----------------

Plumbum.cli prints various messages for the user. These can be localized into your local language; pull requests adding languages are welcome.

To add a language, run ``./translations.py`` from the main github directory, and then copy the file ``plumbum/cli/i18n/messages.pot`` to ``plumbum/cli/i18n/<lang>.po``, and add your language. Run ``./translations.py`` again to update the file you made (save first) and also create the needed files binary file.

See `gettext: PMOTW3 <https://pymotw.com/3/gettext/>`_ for more info.
