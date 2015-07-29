from IPython.core.magic import (Magics, magics_class,
                                cell_magic, needs_local_scope)
import IPython.display

try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
import sys

valid_choices = [x[8:] for x in dir(IPython.display) if 'display_' == x[:8]]

@magics_class
class OutputMagics(Magics):

    @needs_local_scope
    @cell_magic
    def to(self, line, cell, local_ns=None):
        choice = line.strip()
        assert choice in valid_choices, "Valid choices for '%%to' are: "+str(valid_choices)
        display_fn = getattr(IPython.display, "display_"+choice)

        "Captures stdout and renders it in the notebook with some ."
        with StringIO() as out:
            old_out = sys.stdout
            try:
                sys.stdout = out
                exec(cell, self.shell.user_ns, local_ns)
                out.seek(0)
                display_fn(out.getvalue(), raw=True)
            finally:
                sys.stdout = old_out

