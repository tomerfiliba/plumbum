from __future__ import annotations

from unittest.mock import patch

from plumbum.cli import Application, ExistingFile


class App(Application):
    def main(self, file: ExistingFile):
        print(f"file={file.name}")


def test_access_annotations(capsys):
    _, rc = App.run(["prog", "pyproject.toml"], exit=False)
    assert rc == 0
    stdout, _ = capsys.readouterr()
    assert "file=pyproject.toml" in stdout


def test_extra_annotations_ignored(capsys):
    """Test that annotations not corresponding to parameters are safely ignored.
    
    This test simulates a scenario where typing.get_type_hints returns
    annotations that don't correspond to actual function parameters. 
    This could happen in edge cases with class-level annotations or
    other advanced Python features. The code should handle this gracefully
    by skipping annotations that aren't in the parameter list.
    """
    import typing
    
    # Save the original get_type_hints
    original_get_type_hints = typing.get_type_hints
    
    def mock_get_type_hints(obj, *args, **kwargs):
        hints = original_get_type_hints(obj, *args, **kwargs)
        # Add an extra annotation that doesn't correspond to a parameter
        # This simulates the condition that caused the original bug
        if hasattr(obj, '__name__') and obj.__name__ == 'main':
            hints['FileArgument'] = ExistingFile
        return hints
    
    with patch('typing.get_type_hints', side_effect=mock_get_type_hints):
        # This should not crash even with the extra annotation
        _, rc = App.run(["prog", "pyproject.toml"], exit=False)
        assert rc == 0
        stdout, _ = capsys.readouterr()
        assert "file=pyproject.toml" in stdout
