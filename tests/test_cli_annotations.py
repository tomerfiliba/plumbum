from __future__ import annotations

import functools

from plumbum.cli import Application, ExistingFile


def passthrough(func):
    """A decorator that reshapes the signature, as in #755."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class App(Application):
    def main(self, file: ExistingFile):
        print(f"file={file.name}")


class KeywordOnlyApp(Application):
    def main(self, file: ExistingFile, *, verbose: bool = False):
        print(f"file={file.name} verbose={verbose}")


class KeywordArgsApp(Application):
    def main(self, file: ExistingFile, **kwargs: str):
        print(f"file={file.name} kwargs={kwargs}")


class DecoratedApp(Application):
    @passthrough
    def main(self, file: ExistingFile):
        print(f"file={file.name}")


def test_access_annotations(capsys):
    _, rc = App.run(["prog", "pyproject.toml"], exit=False)
    assert rc == 0
    stdout, _ = capsys.readouterr()
    assert "file=pyproject.toml" in stdout


def test_annotated_keyword_only_argument(capsys):
    _, rc = KeywordOnlyApp.run(["prog", "pyproject.toml"], exit=False)
    assert rc == 0
    stdout, _ = capsys.readouterr()
    assert "file=pyproject.toml verbose=False" in stdout


def test_annotated_var_keyword_argument(capsys):
    _, rc = KeywordArgsApp.run(["prog", "pyproject.toml"], exit=False)
    assert rc == 0
    stdout, _ = capsys.readouterr()
    assert "file=pyproject.toml kwargs={}" in stdout


def test_decorated_main_validates(capsys):
    _, rc = DecoratedApp.run(["prog", "pyproject.toml"], exit=False)
    assert rc == 0
    stdout, _ = capsys.readouterr()
    assert "file=pyproject.toml" in stdout

    _, rc = DecoratedApp.run(["prog", "no-such-file.txt"], exit=False)
    assert rc == 2
    stdout, _ = capsys.readouterr()
    assert "no-such-file.txt" in stdout


def test_decorated_main_arity(capsys):
    _, rc = DecoratedApp.run(["prog", "pyproject.toml", "extra"], exit=False)
    assert rc == 2
    stdout, _ = capsys.readouterr()
    assert "Expected at most 1 positional argument" in stdout


def test_decorated_main_usage(capsys):
    _, rc = DecoratedApp.run(["prog", "--help"], exit=False)
    assert rc == 0
    stdout, _ = capsys.readouterr()
    assert "prog [SWITCHES] file" in stdout
