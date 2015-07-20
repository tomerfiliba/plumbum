#!/usr/bin/env python
from __future__ import with_statement, print_function

from plumbum import COLOR

with COLOR.FG.RED:
    print('This is in red')
print('This is completly restored, even if an exception is thrown!')
with COLOR:
    print('It is always a good idea to be in a context manager, to avoid being',
          'left with a colored terminal if there is an exception!')
    print(COLOR.BOLD + "This is bold and exciting!" - COLOR.BOLD)
    print(COLOR.BG.CYAN + "This is on a cyan background." + COLOR.RESET)
    print(COLOR.FG[42] + "If your terminal supports 256 colors, this is colorful!" + COLOR.RESET)
    print()
    for color in COLOR:
        print(color + u'\u2588', end='')
    COLOR.RESET()
    print()
    print('Colors can be reset ' + COLOR.UNDERLINE['Too!'])
    for color in COLOR[:16]:
        print(color["This is in color!"])
