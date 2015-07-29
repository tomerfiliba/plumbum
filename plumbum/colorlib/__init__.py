"""\
The ``ansicolor`` object provides ``bg`` and ``fg`` to access colors,
and attributes like bold and
underlined text. It also provides ``reset`` to recover the normal font.
"""

from plumbum.colorlib.factories import StyleFactory
from plumbum.colorlib.styles import Style, ANSIStyle, HTMLStyle

ansicolors = StyleFactory(ANSIStyle)
htmlcolors = StyleFactory(HTMLStyle)

def load_ipython_extension(ipython):
    try:
        from plumbum.colorlib._ipython_ext import OutputMagics
    except ImportError:
        print("IPython required for the IPython extension to be loaded.")
        raise

    ipython.push({"colors":htmlcolors})
    ipython.register_magics(OutputMagics)

