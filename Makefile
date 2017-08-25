.PRECIOUS: plumbum/cli/i18n/%.po.new
# scrape sources for messages
all: plumbum/cli/i18n/*/LC_MESSAGES/plumbum.cli.mo
plumbum/cli/i18n/messages.pot: plumbum/cli/*.py
	xgettext --from-code utf-8  -L python --keyword=T_ -o $@ $^

# merge changes with previous translations
plumbum/cli/i18n/%.po.new: plumbum/cli/i18n/messages.pot plumbum/cli/i18n/%.po
	$(foreach f,$(filter-out $<,$^),msgmerge $f plumbum/cli/i18n/messages.pot > $(f).new;)

# compile runtime-usable messages
plumbum/cli/i18n/%/LC_MESSAGES/plumbum.cli.mo: plumbum/cli/i18n/%.po.new
	$(foreach f,$^,mkdir -p $(f:.po.new=)/LC_MESSAGES;)
	$(foreach f,$^,msgfmt -o $(f:.po.new=)/LC_MESSAGES/plumbum.cli.mo $(f);)

update_cli_ru:
	mv plumbum/cli/i18n/ru.po.new plumbum/cli/i18n/ru.po
