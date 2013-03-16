"""
a more structured replacement for the built-in ``cmd`` module
"""
import sys

def command(name = None, args = []):
    def deco(func):
        func._command_info = {}
        return func
    return deco

class InteractiveQuit(Exception):
    pass

class Interactive(object):
    PS1 = ">>> "
    PS2 = "... "
    
    def __init__(self):
        pass
    
    def prompt_func(self, initial):
        if initial:
            return self.PS1
        else:
            return self.PS2
    
    def interact(self, stream = sys.stdin):
        try:
            while True:
                finished = False
                prevline = ""
                while True:
                    try:
                        line = stream.readline()
                    except EOFError:
                        raise InteractiveQuit()
                    argv, finished = self._parse_line(prevline + line)
                    if finished:
                        break
                    else:
                        prevline = line
                if not argv:
                    continue
                self._process_line(argv)
        except InteractiveQuit:
            pass
    
    @command
    def help(self):
        pass
    
    @command
    def quit(self):
        raise InteractiveQuit()
    



if __name__ == "__main__":
    class Example(Interactive):
        pass


