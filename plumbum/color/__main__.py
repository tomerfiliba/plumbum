"""
This is provided as a quick way to recover your terminal. Simply run
``python -m plumbum.color``
to recover terminal color.
"""


from plumbum.color import COLOR

if __name__ == '__main__':
    COLOR.use_color=True
    COLOR.RESET()
