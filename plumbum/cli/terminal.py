"""
Terminal-related utilities
"""
from __future__ import division, print_function, absolute_import
import sys
import os
import platform
from struct import Struct
from plumbum import local


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
    elif current_os in ('Linux', 'Darwin', 'FreeBSD') or current_os.startswith('CYGWIN'):
        size = _get_terminal_size_linux()

    if size is None: # we'll assume the standard 80x25 if for any reason we don't know the terminal size
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
        from plumbum.cmd import tput
        cols = int(tput('cols'))
        rows = int(tput('lines'))
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

def readline(message = ""):
    """Gets a line of input from the user (stdin)"""
    sys.stdout.write(message)
    return sys.stdin.readline()

def ask(question, default = None):
    """
    Presents the user with a yes/no question.

    :param question: The question to ask
    :param default: If ``None``, the user must answer. If ``True`` or ``False``, lack of response is
                    interpreted as the default option

    :returns: the user's choice
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
            answer = readline(question).strip().lower()
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

    :returns: The user's choice

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
            choice = readline(msg).strip()
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

def prompt(question, type = int, default = NotImplemented, validator = lambda val: True):
    question = question.rstrip(" \t:")
    if default is not NotImplemented:
        question += " [%s]" % (default,)
    question += ": "
    while True:
        try:
            ans = readline(question).strip()
        except EOFError:
            ans = ""
        if not ans:
            if default is not NotImplemented:
                #sys.stdout.write("\b%s\n" % (default,))
                return default
            else:
                continue
        try:
            ans = type(ans)
        except (TypeError, ValueError) as ex:
            sys.stdout.write("Invalid value (%s), please try again\n" % (ex,))
            continue
        try:
            validator(ans)
        except ValueError as ex:
            sys.stdout.write("%s, please try again\n" % (ex,))
        return ans

def hexdump(data_or_stream, bytes_per_line = 16, aggregate = True):
    """Convert the given bytes (or a stream with a buffering ``read()`` method) to hexdump-formatted lines,
    with possible aggregation of identical lines. Returns a generator of formatted lines.
    """
    if hasattr(data_or_stream, "read"):
        def read_chunk():
            while True:
                buf = data_or_stream.read(bytes_per_line)
                if not buf:
                    break
                yield buf
    else:
        def read_chunk():
            for i in range(0, len(data_or_stream), bytes_per_line):
                yield data_or_stream[i:i + bytes_per_line]
    prev = None
    skipped = False
    for i, chunk in enumerate(read_chunk()):
        hexd = " ".join("%02x" % (ord(ch),) for ch in chunk)
        text = "".join(ch if 32 <= ord(ch) < 127 else "." for ch in chunk)
        if aggregate and prev == chunk:
            skipped = True
            continue
        prev = chunk
        if skipped:
            yield "*"
        yield "%06x | %s| %s" % (i * bytes_per_line, hexd.ljust(bytes_per_line * 3, " "), text)
        skipped = False


def pager(rows, pagercmd = None):
    """Opens a pager (e.g., ``less``) to display the given text. Requires a terminal.

    :param rows: a ``bytes`` or a list/iterator of "rows" (``bytes``)
    :param pagercmd: the pager program to run. Defaults to ``less -RSin``
    """
    if not pagercmd:
        pagercmd = local["less"]["-RSin"]
    if hasattr(rows, "splitlines"):
        rows = rows.splitlines()

    pg = pagercmd.popen(stdout = None, stderr = None)
    try:
        for row in rows:
            line = "%s\n" % (row,)
            try:
                pg.stdin.write(line)
                pg.stdin.flush()
            except IOError:
                break
        pg.stdin.close()
        pg.wait()
    finally:
        try:
            rows.close()
        except Exception:
            pass
        if pg and pg.poll() is None:
            try:
                pg.terminate()
            except Exception:
                pass
            os.system("reset")





