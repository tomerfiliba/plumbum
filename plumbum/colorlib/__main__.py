"""
This is provided as a quick way to recover your terminal. Simply run
``python -m plumbum.colorlib``
to recover terminal color.
"""

from plumbum.colorlib import ansicolors

def main():
    ansicolors.use_color=True
    ansicolors.reset()

if __name__ == '__main__':
    main()
