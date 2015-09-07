#!/usr/bin/env python
from __future__ import with_statement, print_function

from plumbum import colors

with colors.fg.red:
    print('This is in red')

print('This is completly restored, even if an exception is thrown!')

print('The library will restore color on exiting automatially.')
print(colors.bold["This is bold and exciting!"])
print(colors.bg.cyan | "This is on a cyan background.")
print(colors.fg[42] | "If your terminal supports 256 colors, this is colorful!")
print()
for c in colors:
    print(c + u'\u2588', end='')
colors.reset()
print()
print('Colors can be reset ' + colors.underline['Too!'])
for c in colors[:16]:
    print(c["This is in color!"])

colors.red()
print("This should clean up the color automatically on program exit...")
