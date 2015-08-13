
try:
    from IPython.core.magic import (Magics, magics_class,
                                cell_magic, needs_local_scope)
except ImportError:
    print("IPython required for the IPython extension to be loaded.")
    raise

import ast
from plumbum import local, CommandNotFound
try:
    import builtins
except ImportError:
    import __builtins__ as builtins

@magics_class
class AutoMagics(Magics):

    @needs_local_scope
    @cell_magic
    def autocmd(self, line, cell, local_ns=None):
        mod = ast.parse(cell)
        calls = [c for c in ast.walk(mod) if isinstance(c,ast.Call) or isinstance(c, ast.Subscript)]
        for call in calls:
            name = call.func.id if isinstance(call, ast.Call) else call.value.id
            if name not in self.shell.user_ns and name not in dir(builtins):
                try:
                    self.shell.user_ns[name] = local[name]
                except CommandNotFound:
                    pass
        exec(cell, self.shell.user_ns, local_ns)

def load_ipython_extension(ipython):
    ipython.register_magics(AutoMagics)

