from __future__ import with_statement, print_function
import unittest
from plumbum.colorlib.styles import ANSIStyle, Color, AttributeNotFound, ColorNotFound
from plumbum.colorlib.names import color_html, FindNearest


class TestNearestColor(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(FindNearest(0,0,0).all_fast(),0)
        for n,color in enumerate(color_html):
            # Ignoring duplicates
            if n not in (16, 21, 46, 51, 196, 201, 226, 231, 244):
                rgb = (int(color[1:3],16), int(color[3:5],16), int(color[5:7],16))
                self.assertEqual(FindNearest(*rgb).all_fast(),n)

    def test_nearby(self):
        self.assertEqual(FindNearest(1,2,2).all_fast(),0)
        self.assertEqual(FindNearest(7,7,9).all_fast(),232)

    def test_simplecolor(self):
        self.assertEqual(FindNearest(1,2,4).only_basic(), 0)
        self.assertEqual(FindNearest(0,255,0).only_basic(), 2)
        self.assertEqual(FindNearest(100,100,0).only_basic(), 3)
        self.assertEqual(FindNearest(140,140,140).only_basic(), 7)


class TestColorLoad(unittest.TestCase):

    def test_rgb(self):
        blue = Color(0,0,255) # Red, Green, Blue
        self.assertEqual(blue.rgb, (0,0,255))

    def test_simple_name(self):
        green = Color.from_simple('green')
        self.assertEqual(green.number, 2)

    def test_different_names(self):
        self.assertEqual(Color('Dark Blue'),
                         Color('Dark_Blue'))
        self.assertEqual(Color('Dark_blue'),
                         Color('Dark_Blue'))
        self.assertEqual(Color('DARKBLUE'),
                         Color('Dark_Blue'))
        self.assertEqual(Color('DarkBlue'),
                         Color('Dark_Blue'))
        self.assertEqual(Color('Dark Green'),
                         Color('Dark_Green'))

    def test_loading_methods(self):
        self.assertEqual(Color("Yellow"),
                         Color.from_full("Yellow"))
        self.assertNotEqual(Color.from_full("yellow").representation,
                            Color.from_simple("yellow").representation)


class TestANSIColor(unittest.TestCase):
    def setUp(self):
        ANSIStyle.use_color = True

    def test_ansi(self):
        self.assertEqual(str(ANSIStyle(fgcolor=Color('reset'))), '\033[39m')
        self.assertEqual(str(ANSIStyle(fgcolor=Color.from_full('green'))), '\033[38;5;2m')
        self.assertEqual(str(ANSIStyle(fgcolor=Color.from_simple('red'))), '\033[31m')


class TestStyle(unittest.TestCase):
    def setUp(self):
        ANSIStyle.use_color = True

    def test_InvalidAttributes(self):
        pass

class TestNearestColor(unittest.TestCase):
    def test_allcolors(self):
        myrange = (0,1,2,5,17,39,48,73,82,140,193,210,240,244,250,254,255)
        for r in myrange:
            for g in myrange:
                for b in myrange:
                    near = FindNearest(r,g,b)
                    self.assertEqual(near.all_slow(),near.all_fast(), 'Tested: {0}, {1}, {2}'.format(r,g,b))



if __name__ == '__main__':
    unittest.main()
