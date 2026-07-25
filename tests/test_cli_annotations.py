from __future__ import annotations

from plumbum.cli import Application, ExistingFile


class App(Application):
    def main(self, file: ExistingFile):
        print(f"file={file.name}")


class KeywordOnlyApp(Application):
    def main(self, file: ExistingFile, *, verbose: bool = False):
        print(f"file={file.name} verbose={verbose}")


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
