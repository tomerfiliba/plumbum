# Just check to see if this file is importable
from __future__ import annotations

import sys

import pytest

from plumbum.cli.image import Image
from plumbum.colorlib.factories import ColorFactory
from plumbum.colorlib.names import FindNearest, color_html
from plumbum.colorlib.styles import (  # noqa: F401
    ANSIStyle,
    AttributeNotFound,
    Color,
    ColorNotFound,
)


class TestNearestColor:
    def test_exact(self):
        assert FindNearest(0, 0, 0).all_fast() == 0
        for n, color in enumerate(color_html):
            # Ignoring duplicates
            if n not in (16, 21, 46, 51, 196, 201, 226, 231, 244):
                rgb = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
                assert FindNearest(*rgb).all_fast() == n

    def test_nearby(self):
        assert FindNearest(1, 2, 2).all_fast() == 0
        assert FindNearest(7, 7, 9).all_fast() == 232

    def test_simplecolor(self):
        assert FindNearest(1, 2, 4).only_basic() == 0
        assert FindNearest(0, 255, 0).only_basic() == 2
        assert FindNearest(100, 100, 0).only_basic() == 3
        assert FindNearest(140, 140, 140).only_basic() == 7


class TestColorLoad:
    def test_rgb(self):
        blue = Color(0, 0, 255)  # Red, Green, Blue
        assert blue.rgb == (0, 0, 255)

    def test_simple_name(self):
        green = Color.from_simple("green")
        assert green.number == 2

    def test_different_names(self):
        assert Color("Dark Blue") == Color("Dark_Blue")
        assert Color("Dark_blue") == Color("Dark_Blue")
        assert Color("DARKBLUE") == Color("Dark_Blue")
        assert Color("DarkBlue") == Color("Dark_Blue")
        assert Color("Dark Green") == Color("Dark_Green")

    def test_loading_methods(self):
        assert Color("Yellow") == Color.from_full("Yellow")
        assert (
            Color.from_full("yellow").representation
            != Color.from_simple("yellow").representation
        )


class TestANSIColor:
    @classmethod
    def setup_class(cls):
        ANSIStyle.use_color = True

    def test_ansi(self):
        assert str(ANSIStyle(fgcolor=Color("reset"))) == "\033[39m"
        assert str(ANSIStyle(fgcolor=Color.from_full("green"))) == "\033[38;5;2m"
        assert str(ANSIStyle(fgcolor=Color.from_simple("red"))) == "\033[31m"


class TestNearestColorAgain:
    def test_allcolors(self):
        myrange = (
            0,
            1,
            2,
            5,
            17,
            39,
            48,
            73,
            82,
            140,
            193,
            210,
            240,
            244,
            250,
            254,
            255,
        )
        for r in myrange:
            for g in myrange:
                for b in myrange:
                    near = FindNearest(r, g, b)
                    assert near.all_slow() == near.all_fast(), f"Tested: {r}, {g}, {b}"


class TestColorlibCorrectness:
    """Regression tests for colorlib correctness fixes (issue #820)."""

    def test_stdout_none_import(self, monkeypatch):
        """get_color_repr() must not raise when sys.stdout is None (fix 1)."""
        import plumbum.colorlib.styles as styles_mod

        # FORCE_COLOR/NO_COLOR short-circuit before the stdout check (and CI
        # sets FORCE_COLOR), so clear them to exercise the isatty path.
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr(sys, "stdout", None)
        # Should return 0 instead of raising AttributeError
        result = styles_mod.get_color_repr()
        assert result == 0

    def test_stdout_no_isatty(self, monkeypatch):
        """get_color_repr() must not raise when sys.stdout lacks isatty (fix 1)."""
        import plumbum.colorlib.styles as styles_mod

        class NoIsatty:
            pass

        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr(sys, "stdout", NoIsatty())
        result = styles_mod.get_color_repr()
        assert result == 0

    def test_color_zero_is_black(self):
        """Color(0) must produce black, not the reset color (fix 2)."""
        black = Color(0)
        assert not black.isreset, "Color(0) should be black, not reset"
        assert black.number == 0

    def test_color_none_is_reset(self):
        """Color() and Color(None) must produce the reset color (fix 2)."""
        assert Color().isreset
        assert Color(None).isreset

    def test_color_empty_string_is_reset(self):
        """Color('') must produce the reset color (fix 2)."""
        assert Color("").isreset

    def test_color_missing_b_raises(self):
        """Color(r, g) with only two ints must raise ColorNotFound (fix 2)."""
        with pytest.raises(ColorNotFound):
            Color(255, 128)

    def test_color_out_of_range_raises(self):
        """Color(300) must raise ColorNotFound, not AssertionError (fix 3)."""
        with pytest.raises(ColorNotFound):
            Color(300)

    def test_colorfactory_out_of_range_raises(self):
        """ColorFactory[300] must raise ColorNotFound, not AssertionError (fix 3)."""
        factory = ColorFactory(True, ANSIStyle)
        with pytest.raises(ColorNotFound):
            factory[300]

    def test_from_ansi_multiple_sequences(self):
        """from_ansi must parse all escape sequences, not just the first (fix 4)."""
        ANSIStyle.use_color = 4
        style = ANSIStyle.from_ansi("\033[1m\033[31m")
        # Both bold and red fg must be present
        assert style.attributes.get("bold") is True, "bold must be set"
        assert style.fg is not None, "fg must be present"
        assert not style.fg.isreset, "fg must be red (not reset)"

    def test_bold_off_roundtrip(self):
        """ANSIStyle(attributes={'bold': False}) must round-trip through ANSI (fix 5)."""
        ANSIStyle.use_color = 4
        original = ANSIStyle(attributes={"bold": False})
        ansi_str = str(original)
        assert ansi_str, "Expected non-empty ANSI sequence for bold=False"
        recovered = ANSIStyle.from_ansi(ansi_str)
        assert recovered.attributes.get("bold") is False, (
            f"bold must be False after round-trip, got attributes={recovered.attributes!r}"
        )


class TestImageAspect:
    def test_wide_image_stays_wide(self):
        # Regression: a wide image (200x100) on an 80x25 terminal must render
        # wide (fill the width), not tall.
        img = Image()
        width, height = img.best_aspect((200, 100), (80, 25))
        assert width > height
        assert width <= 80
        assert height <= 25
        # fills the available width for this case
        assert width == 80

    def test_tall_image_stays_tall(self):
        img = Image()
        width, height = img.best_aspect((100, 400), (80, 25))
        assert height >= width
        assert width <= 80
        assert height <= 25

    def test_char_ratio_zero_returns_term(self):
        img = Image(char_ratio=0)
        assert img.best_aspect((200, 100), (80, 25)) == (80, 25)
