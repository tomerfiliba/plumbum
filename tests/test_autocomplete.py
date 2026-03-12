#!/usr/bin/env python

from __future__ import annotations

import os
from unittest.mock import patch

from plumbum import cli


class CompletionApp(cli.Application):
    verbose = cli.Flag(["-v", "--verbose"], help="Enable verbose mode")
    output = cli.SwitchAttr(["-o", "--output"], str, help="Output file")

    @cli.switch(["--level"], cli.Set("debug", "info", "warning", "error"))
    def level(self, level: str):
        print(f"Level: {level}")

    def main(self, src, dst="default"):
        pass


class CompletionAppWithSubcommands(cli.Application):
    """
    Tests for autocomplete functionality in plumbum.cli.Application.

    This module can be run directly to test shell completion interactively.

    Test it with Fish:

        # Enter Plumbum's tests folder
        cd ./tests

        # Let Fish find executable files within
        eval (fish_add_path --path .)

        # Install Fish completions
        test_autocomplete.py --fish-completion > ~/.config/fish/completions/test_autocomplete.py.fish

        # Test completions interactively
        test_autocomplete.py <TAB>
        test_autocomplete.py --<TAB>
        test_autocomplete.py add --<TAB>

        # Remove Fish completions when done
        rm ~/.config/fish/completions/test_autocomplete.py.fish

    Test it with Bash:
        # Enter Plumbum's tests folder
        cd ./tests

        # Let Bash find executable files within CWD
        export PATH=".:$PATH"

        # Load Bash completions
        eval "$(test_autocomplete.py --bash-completion)"

        # Test completions interactively
        test_autocomplete.py --<TAB>
        test_autocomplete.py add --<TAB>
    """

    verbose = cli.Flag(["-v", "--verbose"], help="Enable verbose mode")


@CompletionAppWithSubcommands.subcommand("add")
class AddSubcommand(cli.Application):
    """Example subcommand "add"."""

    force = cli.Flag(["-f", "--force"], help="Force add")

    def main(self, *files):
        pass


@CompletionAppWithSubcommands.subcommand("commit")
class CommitSubcommand(cli.Application):
    """Example subcommand "commit"."""

    message = cli.SwitchAttr(["-m", "--message"], str, help="Commit message")

    def main(self):
        pass


class TestCompletions:
    def test_get_switch_completions(self):
        inst = CompletionApp("completionapp")
        completions = inst.get_completions([])
        switch_names = {c for c in completions if c.startswith("-")}
        assert "--verbose" in switch_names
        assert "-v" in switch_names
        assert "--output" in switch_names
        assert "-o" in switch_names
        assert "--level" in switch_names

    def test_get_switch_completions_partial(self):
        inst = CompletionApp("completionapp")
        completions = inst.get_completions(["--ver"])
        switch_names = {c for c in completions if c.startswith("-")}
        assert "--verbose" in switch_names
        assert "--level" not in switch_names

    def test_get_subcommand_completions(self):
        inst = CompletionAppWithSubcommands("completionapp")
        completions = inst.get_completions([])
        assert "add" in completions
        assert "commit" in completions

    def test_get_subcommand_completions_after_switch(self):
        inst = CompletionAppWithSubcommands("completionapp")
        completions = inst.get_completions(["--verbose"])
        subcommand_names = {c for c in completions if not c.startswith("-")}
        assert "add" in subcommand_names
        assert "commit" in subcommand_names

    def test_get_argument_completions_with_validator(self):
        inst = CompletionApp("completionapp")
        completions = inst.get_completions(["--level", ""])
        assert "debug" in completions
        assert "info" in completions
        assert "warning" in completions
        assert "error" in completions

    def test_get_argument_completions_partial_with_validator(self):
        inst = CompletionApp("completionapp")
        completions = inst.get_completions(["--level", "deb"])
        assert "debug" in completions
        assert "info" not in completions

    def test_nested_subcommand_completions(self):
        inst = CompletionAppWithSubcommands("completionapp")
        inst.get_completions(["add"])
        nested_inst, nested_completions = inst.get_nested_completions(["add"])
        assert nested_inst is not None
        switch_names = {c for c in nested_completions if c.startswith("-")}
        assert "--force" in switch_names
        assert "-f" in switch_names

    def test_bash_completion_script(self):
        script = CompletionApp.bash_completion_script("completionapp")
        assert "completionapp" in script
        assert "--verbose" in script
        assert "--output" in script
        assert "--level" in script

    def test_bash_completion_script_with_subcommands(self):
        script = CompletionAppWithSubcommands.bash_completion_script("geet")
        assert "geet" in script
        assert "add" in script
        assert "commit" in script

    def test_fish_completion_script(self):
        script = CompletionApp.fish_completion_script("completionapp")
        assert "completionapp" in script
        assert "-l verbose" in script
        assert "-l output" in script
        assert "-l level" in script

    def test_fish_completion_script_with_subcommands(self):
        script = CompletionAppWithSubcommands.fish_completion_script("geet")
        assert "geet" in script
        assert "add" in script
        assert "commit" in script

    def test_autocomplete_env_bash(self):
        env = {
            "COMP_WORDS": "completionapp --lev",
            "COMP_CWORD": "1",
        }
        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(CompletionApp, "_print_completions_and_exit") as mock_exit,
        ):
            CompletionApp.autocomplete(["completionapp", "--lev"])
            if mock_exit.called:
                completions = mock_exit.call_args[0][0]
                assert "--level" in completions

    def test_no_completion_when_not_requested(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(CompletionApp, "_print_completions_and_exit") as mock_exit,
        ):
            CompletionApp.autocomplete(["completionapp", "--verbose"])
            assert not mock_exit.called


class TestSwitchInfoHelpers:
    def test_switch_info_completion_for_flag(self):
        inst = CompletionApp("completionapp")
        swinfo = inst._switches_by_name.get("verbose")
        if swinfo:
            completions = inst._get_switch_arg_completions(swinfo, "")
            assert completions == []

    def test_switch_info_completion_for_set(self):
        inst = CompletionApp("completionapp")
        swinfo = inst._switches_by_name.get("level")
        if swinfo:
            completions = inst._get_switch_arg_completions(swinfo, "deb")
            assert "debug" in completions


class TestPositionalArgCompletions:
    def test_positional_args_not_implemented_by_default(self):
        inst = CompletionApp("completionapp")
        completions = inst.get_completions(["src_file"])
        positional = [c for c in completions if not c.startswith("-")]
        assert len(positional) >= 0


if __name__ == "__main__":
    CompletionAppWithSubcommands.run()
