"""
Terminal-related utilities
"""
import sys
import os
import platform
import subprocess
from struct import Struct
from plumbum.lib import six


def get_terminal_size():
    """
    Get width and height of console; works on linux, os x, windows and cygwin

    Adapted from https://gist.github.com/jtriley/1108174
    Originally from: http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    current_os = platform.system()
    if current_os == 'Windows':
        size = _get_terminal_size_windows()
        if not size:
            # needed for window's python in cygwin's xterm!
            size = _get_terminal_size_tput()
    elif current_os in ('Linux', 'Darwin') or current_os.startswith('CYGWIN'):
        size = _get_terminal_size_linux()
    if not size:
        size = (80, 25)
    return size

def _get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        STDERR_HANDLE = -12
        h = windll.kernel32.GetStdHandle(STDERR_HANDLE)
        csbi_struct = Struct("hhhhHhhhhhh")
        csbi = create_string_buffer(csbi_struct.size)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            _, _, _, _, _, left, top, right, bottom, _, _ = csbi_struct.unpack(csbi.raw)
            return right - left + 1, bottom - top + 1
        return None
    except Exception:
        return None

def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:
        cols = int(subprocess.check_call(['tput', 'cols']))
        rows = int(subprocess.check_call(['tput', 'lines']))
        return (cols, rows)
    except Exception:
        return None

def _ioctl_GWINSZ(fd):
    yx = Struct("hh")
    try:
        import fcntl
        import termios
        return yx.unpack(fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except Exception:
        return None

def _get_terminal_size_linux():
    cr = _ioctl_GWINSZ(0) or _ioctl_GWINSZ(1) or _ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = _ioctl_GWINSZ(fd)
            os.close(fd)
        except Exception:
            pass
    if not cr:
        try:
            cr = (int(os.environ['LINES']), int(os.environ['COLUMNS']))
        except Exception:
            return None
    return cr[1], cr[0]

def input(message = ""):                         # @ReservedAssignment                          
    """Gets free-text input from the user"""
    sys.stdout.write(message)
    return sys.stdin.readline()

def ask(question, default = None):
    """
    Presents the user with a yes/no question. 
    
    :param question: The question to ask
    :param default: If ``None``, the user must answer. If ``True`` or ``False``, lack of response is 
                    interpreted as the default option
    """
    question = question.rstrip().rstrip("?").rstrip() + "?"
    if default is None:
        question += " (y/n) "
    elif default:
        question += " [Y/n] "
    else:
        question += " [y/N] "
    
    while True:
        try:
            answer = input(question).strip().lower()
        except EOFError:
            answer = None
        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no"):
            return False
        elif not answer and default is not None:
            return default
        else:
            sys.stdout.write("Invalid response, please try again\n")

def choose(question, options, default = None):
    """Prompts the user with a question and a set of options, from which the user need choose.
    
    :param question: The question to ask
    :param options: A set of options. It can be a list (of strings or two-tuples, mapping text 
                    to returned-object) or a dict (mapping text to returned-object).``
    :param default: If ``None``, the user must answer. Otherwise, lack of response is interpreted
                    as this answer
    
    :returns: The 
    
    Example::
    
        ans = choose("What is your favorite color?", ["blue", "yellow", "green"], default = "yellow")
        # `ans` will be one of "blue", "yellow" or "green"

        ans = choose("What is your favorite color?", 
                {"blue" : 0x0000ff, "yellow" : 0xffff00 , "green" : 0x00ff00}, default = 0x00ff00)
        # this will display "blue", "yellow" and "green" but return a numerical value
    """
    if hasattr(options, "items"):
        options = options.items()
    sys.stdout.write(question.rstrip() + "\n")
    choices = {}
    defindex = None
    for i, item in enumerate(options):
        i = i + 1 # python2.5
        if isinstance(item, (tuple, list)) and len(item) == 2:
            text = item[0]
            val = item[1]
        else:
            text = item
            val = item
        choices[i] = val
        if default is not None and default == val:
            defindex = i
        sys.stdout.write("(%d) %s\n" % (i, text))
    if default is not None:
        if defindex is None:
            msg = "Choice [%s]: " % (default,)
        else:
            msg = "Choice [%d]: " % (defindex,)
    else:
        msg = "Choice: "
    while True:
        try:
            choice = input(msg).strip()
        except EOFError:
            choice = ""
        if not choice and default:
            return default
        try:
            choice = int(choice)
            if choice not in choices:
                raise ValueError()
        except ValueError:
            sys.stdout.write("Invalid choice, please try again\n")
            continue
        return choices[choice]

    







