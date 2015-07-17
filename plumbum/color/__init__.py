"""\
The ``COLOR`` object provides ``BG`` and ``FG`` to access colors,
and attributes like bold and
underlined text. It also provides ``RESET`` to recover the normal font.
"""

from plumbum.color.factories import StyleFactory
from plumbum.color.styles import Style, ANSIStyle

COLOR = StyleFactory(ANSIStyle)

