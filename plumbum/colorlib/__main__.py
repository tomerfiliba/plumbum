"""
This is provided as a quick way to recover your terminal. Simply run
``python -m plumbum.colorlib``
to recover terminal color.
"""

from plumbum.colorlib import ansicolors, ColorNotFound
import sys

def main():
    color = ' '.join(sys.argv[1:]) if  len(sys.argv) > 1 else None
    ansicolors.use_color=True
    if color is None:
        ansicolors.reset()
    else:
        names = color.replace('.', ' ').split()
        prev = ansicolors
        for name in names:
            try:
                prev = getattr(prev, name)
            except AttributeError:
                try:
                    prev = prev(int(name))
                except (ColorNotFound, ValueError):
                    prev = prev(name)
        prev()


if __name__ == '__main__':
    main()
