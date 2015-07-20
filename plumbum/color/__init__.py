"""\
The ``COLOR`` object provides ``BG`` and ``FG`` to access colors,
and attributes like bold and
underlined text. It also provides ``RESET`` to recover the normal font.
"""

from plumbum.color.factories import StyleFactory
from plumbum.color.styles import Style, ANSIStyle, HTMLStyle

COLOR = StyleFactory(ANSIStyle)
HTMLCOLOR = StyleFactory(HTMLStyle)

def load_ipython_extension(ipython):
    try:
        from plumbum.color._ipython_ext import OutputMagics
    except ImportError:
        print("IPython required for the IPython extension to be loaded.")
        raise

    ipython.push({"COLOR":HTMLCOLOR})
    ipython.register_magics(OutputMagics)

