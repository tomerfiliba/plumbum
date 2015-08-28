"""\
The ``ansicolor`` object provides ``bg`` and ``fg`` to access colors,
and attributes like bold and
underlined text. It also provides ``reset`` to recover the normal font.
"""

from plumbum.colorlib.factories import StyleFactory
from plumbum.colorlib.styles import Style, ANSIStyle, HTMLStyle, ColorNotFound

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

def main():
    """Color changing script entry. Call using
    python -m plumbum.colors, will reset if no arguements given."""
    import sys
    color = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    ansicolors.use_color=True
    ansicolors.get_colors_from_string(color).now()


