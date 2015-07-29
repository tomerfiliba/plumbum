"""
This is provided as a quick way to recover your terminal. Simply run
``python -m plumbum.colorlib``
to recover terminal color.
"""


from plumbum.colorlib import ansicolor

def main():
    ansicolor.use_color=True
    ansicolor.reset()

if __name__ == '__main__':
    main()
