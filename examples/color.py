#!/usr/bin/env python
from __future__ import with_statement, print_function

from plumbum import colors

with colors.fg.red:
    print('This is in red')

print('This is completly restored, even if an exception is thrown!')

with colors:
    print('It is always a good idea to be in a context manager, to avoid being',
          'left with a colorsed terminal if there is an exception!')
    print(colors.bold + "This is bold and exciting!" - colors.bold)
    print(colors.bg.cyan + "This is on a cyan background." + colors.reset)
    print(colors.fg[42] + "If your terminal supports 256 colorss, this is colorsful!" + colors.reset)
    print()
    for c in colors:
        print(c + u'\u2588', end='')
    colors.reset()
    print()
    print('Colors can be reset ' + colors.underline['Too!'])
    for c in colors[:16]:
        print(c["This is in colors!"])

