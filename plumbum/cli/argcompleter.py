#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import os
import sys
import locale

sys_encoding = locale.getpreferredencoding()

class ArgCompleter(object):
    """


    To run `./prog` in debug mode, try:

        _ARGCOMPLETE=2 COMP_LINE='python argcomp.py one twopython ' COMP_POINT='11' _DEBUG=0 _ARGCOMPLETE_IFS=" " ./prog 8>&1

    """

    def __init__(self):
        self.active = "_ARGCOMPLETE" in os.environ and int(os.environ["_ARGCOMPLETE"]) in [1,2]
        self.debug = bool(int(os.environ.get('_DEBUG', 0)))

        if not self.active:
            return

        try:
            self.debug_stream = os.fdopen(9, "w")
        except OSError:
            self.debug_stream = sys.stderr

        try:
            self.output_stream = os.fdopen(8, "wb")
        except OSError:
            self.debug_stream.write('Not able to open file discriptors, uses fd 8')
            os._exit(1)

        try:
            self.ifs = os.environ.get("_ARGCOMPLETE_IFS", "\013")
            comp_line = os.environ["COMP_LINE"]
            comp_point = int(os.environ["COMP_POINT"])
        except KeyError:
            self.debug_stream.write('Not able to find the completer variables')
            os._exit(1)

        # Adjustment for wide chars
        if sys.version_info < (3, 0):
            comp_point = len(comp_line[:comp_point].decode(sys_encoding))
        else:
            comp_point = len(comp_line.encode(sys_encoding)[:comp_point].decode(sys_encoding))

        self.comp_line = comp_line if isinstance(comp_line, str) else comp_line.decode(sys_encoding)
        self.comp_point = comp_point

        # Supports spaces at the beginning of the line (no history in bash)
        while self.comp_line and self.comp_line[0] == ' ':
            self.comp_line = self.comp_line[1:]
            self.comp_point -= 1

        # Shell hook recognized the first word as the interpreter; discard it
        if int(os.environ["_ARGCOMPLETE"]) == 2:
            loc = self.comp_line.find(' ') + 1
            self.comp_line = self.comp_line[loc:]
            self.comp_point =  self.comp_point - loc

    def send_completions(self, completions):
        if completions is None:
            completions = []
        if not self.active:
            return
        if not self.debug:
            self.output_stream.write(self.ifs.join(completions).encode(sys_encoding))
        else:
            self.debug_stream.write("\nWould have written: '{}' to completer\n".format('|'.join(completions)))

    def get_line(self):
        return self.comp_line, self.comp_point

    def done(self):
        if not self.active:
            return
        self.output_stream.flush()
        self.debug_stream.flush()
        os._exit(0)

if __name__ == '__main__':
    ac = ArgCompleter()
    ac.send_completions(['wowsa'])
    ac.done()
    print("This is a test program")
