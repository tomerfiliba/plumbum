# -*- coding: utf-8 -*-
import pytest

# Just check to see if this file is importable
from plumbum.cli.image import Image
from plumbum.colorlib.names import FindNearest, color_html
from plumbum.colorlib.styles import ANSIStyle, AttributeNotFound, Color, ColorNotFound


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


class TestNearestColor:
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
                    assert (
                        near.all_slow() == near.all_fast()
                    ), "Tested: {}, {}, {}".format(r, g, b)
