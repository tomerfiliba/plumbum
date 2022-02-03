#!/usr/bin/env python3

from plumbum import colors

with colors.fg.red:
    print("This is in red")

print("This is completely restored, even if an exception is thrown!")

print("The library will restore color on exiting automatically.")
print(colors.bold["This is bold and exciting!"])
print(colors.bg.cyan | "This is on a cyan background.")
print(colors.fg[42] | "If your terminal supports 256 colors, this is colorful!")
print()
for c in colors:
    print(c + "\u2588", end="")
colors.reset()
print()
print("Colors can be reset " + colors.underline["Too!"])
for c in colors[:16]:
    print(c["This is in color!"])

colors.red()
print("This should clean up the color automatically on program exit...")
