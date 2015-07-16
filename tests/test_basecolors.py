from __future__ import with_statement, print_function
import unittest
from plumbum.color.base import Style, Color
from plumbum.color.names import find_nearest_color, color_html_full, find_nearest_simple_color


class TestNearestColor(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(find_nearest_color(0,0,0),0)
        for n,color in enumerate(color_html_full):
            # Ignoring duplicates
            if n not in (16, 21, 46, 51, 196, 201, 226, 231, 244):
                rgb = (int(color[1:3],16), int(color[3:5],16), int(color[5:7],16))
                self.assertEqual(find_nearest_color(*rgb),n)

    def test_nearby(self):
        self.assertEqual(find_nearest_color(1,2,2),0)
        self.assertEqual(find_nearest_color(7,7,9),232)

    def test_simplecolor(self):
        self.assertEqual(find_nearest_simple_color(1,2,4), 0)
        self.assertEqual(find_nearest_simple_color(0,255,0), 2)
        self.assertEqual(find_nearest_simple_color(100,100,0), 3)
        self.assertEqual(find_nearest_simple_color(140,140,140), 7)



class TestColorLoad(unittest.TestCase):
    def setUp(self):
        Color.use_color = True

    def test_rgb(self):
        blue = Color(0,0,255) # Red, Green, Blue
        self.assertEqual(blue.r, 0)
        self.assertEqual(blue.g, 0)
        self.assertEqual(blue.b, 255)

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
        self.assertNotEqual(Color.from_full("yellow"),
                            Color.from_simple("yellow"))


class TestANSIColor(unittest.TestCase):
    def setUp(self):
        Color.use_color = True

    def test_ansi(self):
        self.assertEqual(str(Color('reset')), '\033[39m')
        self.assertEqual(str(Color('green')), '\033[38;5;2m')
        self.assertEqual(str(Color.from_simple('red')), '\033[31m')

class TestStyle(unittest.TestCase):
    def setUp(self):
        Color.use_color = True

    def test_style(self):
        pass



if __name__ == '__main__':
    unittest.main()
