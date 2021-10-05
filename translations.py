#!/usr/bin/env python
# -*- coding: utf-8 -*-

# If you are on macOS and using brew, you might need the following first:
# export PATH="/usr/local/opt/gettext/bin:$PATH"

from plumbum import FG, local
from plumbum.cmd import msgfmt, msgmerge, xgettext

translation_dir = local.cwd / "plumbum/cli/i18n"
template = translation_dir / "messages.pot"

(
    xgettext[
        "--from-code",
        "utf-8",
        "-L",
        "python",
        "--keyword=T_",
        "--package-name=Plumbum.cli",
        "-o",
        template,
        sorted(x - local.cwd for x in local.cwd / "plumbum/cli" // "*.py"),
    ]
    & FG
)

for translation in translation_dir // "*.po":
    lang = translation.stem
    new_tfile = translation.with_suffix(".po.new")

    # Merge changes to new file
    (msgmerge[translation, template] > new_tfile) & FG

    new_tfile.move(translation)

    # Render new file into runtime output
    local_dir = translation_dir / lang / "LC_MESSAGES"
    if not local_dir.exists():
        local_dir.mkdir()
    msgfmt["-o", local_dir / "plumbum.cli.mo", translation] & FG
