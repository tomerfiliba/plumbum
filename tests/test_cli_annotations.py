from __future__ import annotations

from plumbum.cli import Application, ExistingFile


class App(Application):
    def main(self, file: ExistingFile):
        print(f"file={file.name}")


def test_access_annotations(capsys):
    _, rc = App.run(["prog", "pyproject.toml"], exit=False)
    assert rc == 0
    stdout, stderr = capsys.readouterr()
    assert "file=pyproject.toml" in stdout
