import os
import sys
import inspect
from plumbum.lib import six
from textwrap import TextWrapper
from plumbum.cli.terminal import get_terminal_size
from plumbum.cli.switches import (SwitchError, UnknownSwitch, MissingArgument, WrongArgumentType,
    MissingMandatorySwitch, SwitchCombinationError, PositionalArgumentsError, switch,
    SubcommandError)


class ShowHelp(SwitchError):
    pass
class ShowVersion(SwitchError):
    pass

class SwitchParseInfo(object):
    __slots__ = ["swname", "val", "index"]
    def __init__(self, swname, val, index):
        self.swname = swname
        self.val = val
        self.index = index

class Subcommand(object):
    def __init__(self, name, subapplication):
        self.name = name
        self.subapplication = subapplication
    def get(self):
        if isinstance(self.subapplication, str):
            modname, clsname = self.subapplication.rsplit(".", 1)
            mod = __import__(modname, None, None, "*")
            try:
                cls = getattr(mod, clsname)
            except AttributeError:
                raise ImportError("cannot import name %s" % (clsname,))
            self.subapplication = cls
        return self.subapplication

    def __repr__(self):
        return "Subcommand(%r, %r)" % (self.name, self.subapplication)


#===================================================================================================
# CLI Application base class
#===================================================================================================

class Application(object):
    """
    The base class for CLI applications; your "entry point" class should derive from it,
    define the relevant switch functions and attributes, and the ``main()`` function.
    The class defines two overridable "meta switches" for version (``-v``, ``--version``)
    and help (``-h``, ``--help``).

    The signature of the main function matters: any positional arguments (e.g., non-switch
    arguments) given on the command line are passed to the ``main()`` function; if you wish
    to allow unlimited number of positional arguments, use varargs (``*args``). The names
    of the arguments will be shown in the help message.

    The classmethod ``run`` serves as the entry point of the class. It parses the command-line
    arguments, invokes switch functions and enter ``main``. You should **not override** this
    method.

    Usage::

        class FileCopier(Application):
            stat = Flag("p", "copy stat info as well")

            def main(self, src, dst):
                if self.stat:
                    shutil.copy2(src, dst)
                else:
                    shutil.copy(src, dst)

        if __name__ == "__main__":
            FileCopier.run()

    There are several class-level attributes you may set:

    * ``PROGNAME`` - the name of the program; if ``None`` (the default), it is set to the
      name of the executable (``argv[0]``)

    * ``VERSION`` - the program's version (defaults to ``1.0``)

    * ``DESCRIPTION`` - a short description of your program (shown in help). If not set,
      the class' ``__doc__`` will be used.

    * ``USAGE`` - the usage line (shown in help)

    A note on sub-commands: when an application is the root, its ``parent`` attribute is set to
    ``None``. When it is used as a nested-command, ``parent`` will point to be its direct ancestor.
    Likewise, when an application is invoked with a sub-command, its ``nested_command`` attribute
    will hold the chosen sub-application and its command-line arguments (a tuple); otherwise, it
    will be set to ``None``
    """

    PROGNAME = None
    DESCRIPTION = None
    VERSION = None
    USAGE = None

    parent = None
    nested_command = None
    _unbound_switches = ()

    def __init__(self, executable):
        if self.PROGNAME is None:
            self.PROGNAME = os.path.basename(executable)
        if self.DESCRIPTION is None:
            self.DESCRIPTION = inspect.getdoc(self)

        self.executable = executable
        self._switches_by_name = {}
        self._switches_by_func = {}
        self._subcommands = {}

        for cls in reversed(type(self).mro()):
            for obj in cls.__dict__.values():
                if isinstance(obj, Subcommand):
                    if obj.name.startswith("-"):
                        raise SubcommandError("Subcommand names cannot start with '-'")
                    # it's okay for child classes to override subcommands set by their parents
                    self._subcommands[obj.name] = obj
                    continue

                swinfo = getattr(obj, "_switch_info", None)
                if not swinfo:
                    continue
                for name in swinfo.names:
                    if name in self._unbound_switches:
                        continue
                    if name in self._switches_by_name and not self._switches_by_name[name].overridable:
                        raise SwitchError("Switch %r already defined and is not overridable" % (name,))
                    self._switches_by_name[name] = swinfo
                    self._switches_by_func[swinfo.func] = swinfo

    @classmethod
    def unbind_switches(cls, *switch_names):
        """Unbinds the given switch names from this application. For example
        
        ::

            class MyApp(cli.Application):
                pass
            MyApp.unbind("--version")
        
        """
        cls._unbound_switches += tuple(name.lstrip("-") for name in switch_names if name)

    @classmethod
    def subcommand(cls, name, subapp = None):
        """Registers the given sub-application as a sub-command of this one. This method can be
        used both as a decorator and as a normal ``classmethod``::

            @MyApp.subcommand("foo")
            class FooApp(cli.Application):
                pass

        Or ::

            MyApp.subcommand("foo", FooApp)

        .. versionadded:: 1.1

        .. versionadded:: 1.3
            The subcommand can also be a string, in which case it is treated as a
            fully-qualified class name and is imported on demand. For examples,

            MyApp.subcommand("foo", "fully.qualified.package.FooApp")

        """
        def wrapper(subapp):
            attrname = "_subcommand_%s" % (subapp if isinstance(subapp, str) else subapp.__name__,)
            setattr(cls, attrname, Subcommand(name, subapp))
            return subapp
        return wrapper(subapp) if subapp else wrapper

    def _parse_args(self, argv):
        tailargs = []
        swfuncs = {}
        index = 0
        while argv:
            index += 1
            a = argv.pop(0)
            if a == "--":
                # end of options, treat the rest as tailargs
                tailargs.extend(argv)
                break

            if a in self._subcommands:
                subcmd = self._subcommands[a].get()
                self.nested_command = (subcmd, [self.PROGNAME + " " + a] + argv)
                break

            elif a.startswith("--") and len(a) >= 3:
                # [--name], [--name=XXX], [--name, XXX], [--name, ==, XXX],
                # [--name=, XXX], [--name, =XXX]
                eqsign = a.find("=")
                if eqsign >= 0:
                    name = a[2:eqsign]
                    argv.insert(0, a[eqsign:])
                else:
                    name = a[2:]
                swname = "--" + name
                if name not in self._switches_by_name:
                    raise UnknownSwitch("Unknown switch %s" % (swname,))
                swinfo = self._switches_by_name[name]
                if swinfo.argtype:
                    if not argv:
                        raise MissingArgument("Switch %s requires an argument" % (swname,))
                    a = argv.pop(0)
                    if a and a[0] == "=":
                        if len(a) >= 2:
                            val = a[1:]
                        else:
                            if not argv:
                                raise MissingArgument("Switch %s requires an argument" % (swname))
                            val = argv.pop(0)
                    else:
                        val = a

            elif a.startswith("-") and len(a) >= 2:
                # [-a], [-a, XXX], [-aXXX], [-abc]
                name = a[1]
                swname = "-" + name
                if name not in self._switches_by_name:
                    raise UnknownSwitch("Unknown switch %s" % (swname,))
                swinfo = self._switches_by_name[name]
                if swinfo.argtype:
                    if len(a) >= 3:
                        val = a[2:]
                    else:
                        if not argv:
                            raise MissingArgument("Switch %s requires an argument" % (swname,))
                        val = argv.pop(0)
                elif len(a) >= 3:
                    argv.insert(0, "-" + a[2:])

            else:
                if a.startswith("-"):
                    raise UnknownSwitch("Unknown switch %s" % (a,))
                tailargs.append(a)
                continue

            # handle argument
            if swinfo.argtype:
                try:
                    val = swinfo.argtype(val)
                except (TypeError, ValueError):
                    ex = sys.exc_info()[1]  # compat
                    raise WrongArgumentType("Argument of %s expected to be %r, not %r:\n    %r" % (
                        swname, swinfo.argtype, val, ex))
            else:
                val = NotImplemented

            if swinfo.func in swfuncs:
                if swinfo.list:
                    swfuncs[swinfo.func].val[0].append(val)
                else:
                    if swfuncs[swinfo.func].swname == swname:
                        raise SwitchError("Switch %r already given" % (swname,))
                    else:
                        raise SwitchError("Switch %r already given (%r is equivalent)" % (
                            swfuncs[swinfo.func].swname, swname))
            else:
                if swinfo.list:
                    swfuncs[swinfo.func] = SwitchParseInfo(swname, ([val],), index)
                elif val is NotImplemented:
                    swfuncs[swinfo.func] = SwitchParseInfo(swname, (), index)
                else:
                    swfuncs[swinfo.func] = SwitchParseInfo(swname, (val,), index)

        return swfuncs, tailargs

    def _validate_args(self, swfuncs, tailargs):
        if six.get_method_function(self.help) in swfuncs:
            raise ShowHelp()
        if six.get_method_function(self.version) in swfuncs:
            raise ShowVersion()

        requirements = {}
        exclusions = {}
        for swinfo in self._switches_by_func.values():
            if swinfo.mandatory and not swinfo.func in swfuncs:
                raise MissingMandatorySwitch("Switch %s is mandatory" %
                    ("/".join(("-" if len(n) == 1 else "--") + n for n in swinfo.names),))
            requirements[swinfo.func] = set(self._switches_by_name[req] for req in swinfo.requires)
            exclusions[swinfo.func] = set(self._switches_by_name[exc] for exc in swinfo.excludes)

        # TODO: compute topological order

        gotten = set(swfuncs.keys())
        for func in gotten:
            missing = set(f.func for f in requirements[func]) - gotten
            if missing:
                raise SwitchCombinationError("Given %s, the following are missing %r" %
                    (swfuncs[func].swname, [self._switches_by_func[f].names[0] for f in missing]))
            invalid = set(f.func for f in exclusions[func]) & gotten
            if invalid:
                raise SwitchCombinationError("Given %s, the following are invalid %r" %
                    (swfuncs[func].swname, [swfuncs[f].swname for f in invalid]))

        m_args, m_varargs, _, m_defaults = inspect.getargspec(self.main)
        max_args = six.MAXSIZE if m_varargs else len(m_args) - 1
        min_args = len(m_args) - 1 - (len(m_defaults) if m_defaults else 0)
        if len(tailargs) < min_args:
            raise PositionalArgumentsError("Expected at least %d positional arguments, got %r" %
                (min_args, tailargs))
        elif len(tailargs) > max_args:
            raise PositionalArgumentsError("Expected at most %d positional arguments, got %r" %
                (max_args, tailargs))

        ordered = [(f, a) for _, f, a in
            sorted([(sf.index, f, sf.val) for f, sf in swfuncs.items()])]
        return ordered, tailargs

    @classmethod
    def run(cls, argv = sys.argv, exit = True):  # @ReservedAssignment
        """
        Runs the application, taking the arguments from ``sys.argv`` by default. If ``exit`` is
        ``True`` (the default), the function will exit with the appropriate return code;
        otherwise it will return a tuple of ``(inst, retcode)``, where ``inst`` is the
        application instance created internally by this function and ``retcode`` is the
        exit code of the application.

        .. note::
           Setting ``exit`` to ``False`` is intendend for testing/debugging purposes only -- do
           not override it other situations.
        """
        argv = list(argv)
        inst = cls(argv.pop(0))
        retcode = 0
        try:
            swfuncs, tailargs = inst._parse_args(argv)
            ordered, tailargs = inst._validate_args(swfuncs, tailargs)
        except ShowHelp:
            inst.help()
        except ShowVersion:
            inst.version()
        except SwitchError:
            ex = sys.exc_info()[1]  # compatibility with python 2.5
            print("Error: %s" % (ex,))
            print("------")
            inst.help()
            retcode = 2
        else:
            for f, a in ordered:
                f(inst, *a)
            retcode = inst.main(*tailargs)
            if not retcode and inst.nested_command:
                subapp, argv = inst.nested_command
                subapp.parent = inst
                inst, retcode = subapp.run(argv, exit = False)

            if retcode is None:
                retcode = 0

        if exit:
            sys.exit(retcode)
        else:
            return inst, retcode

    def main(self, *args):
        """Implement me (no need to call super)"""
        if self._subcommands:
            if args:
                print("Unknown sub-command %r" % (args[0],))
                print("------")
                self.help()
                return 1
            if not self.nested_command:
                print("No sub-command given")
                print("------")
                self.help()
                return 1
        else:
            print("main() not implemented")
            return 1

    @switch(["-h", "--help"], overridable = True, group = "Meta-switches")
    def help(self):  # @ReservedAssignment
        """Prints this help message and quits"""
        self.version()
        if self.DESCRIPTION:
            print(self.DESCRIPTION.strip())

        m_args, m_varargs, _, m_defaults = inspect.getargspec(self.main)
        tailargs = m_args[1:]  # skip self
        if m_defaults:
            for i, d in enumerate(reversed(m_defaults)):
                tailargs[-i - 1] = "[%s=%r]" % (tailargs[-i - 1], d)
        if m_varargs:
            tailargs.append("%s..." % (m_varargs,))
        tailargs = " ".join(tailargs)

        print("")
        if not self.USAGE:
            if self._subcommands:
                self.USAGE = "Usage: %(progname)s [SWITCHES] [SUBCOMMAND [SWITCHES]] %(tailargs)s"
            else:
                self.USAGE = "Usage: %(progname)s [SWITCHES] %(tailargs)s"
        print(self.USAGE % {"progname": self.PROGNAME, "tailargs": tailargs})

        by_groups = {}
        for si in self._switches_by_func.values():
            if si.group not in by_groups:
                by_groups[si.group] = []
            by_groups[si.group].append(si)

        def switchs(by_groups, show_groups):
            for grp, swinfos in sorted(by_groups.items(), key = lambda item: item[0]):
                if show_groups:
                    print("%s:" % (grp,))

                for si in sorted(swinfos, key = lambda si: si.names):
                    swnames = ", ".join(("-" if len(n) == 1 else "--") + n for n in si.names
                        if n in self._switches_by_name and self._switches_by_name[n] == si)
                    if si.argtype:
                        if isinstance(si.argtype, type):
                            typename = si.argtype.__name__
                        else:
                            typename = str(si.argtype)
                        argtype = " %s:%s" % (si.argname.upper(), typename)
                    else:
                        argtype = ""
                    prefix = swnames + argtype
                    yield si, prefix

                if show_groups:
                    print("")

        sw_width = 0

        for si, prefix in switchs(by_groups, False):
            sw_width = max(sw_width, len(prefix))
        if sw_width > 60:
            sw_width = 60

        cols, _ = get_terminal_size()
        min_msg_width = 50
        description_indent = "    %s%s%s"
        wrapper = TextWrapper(width = max(cols - sw_width, min_msg_width) - 2)
        indentation = "\n" + " " * (cols - wrapper.width)

        for si, prefix in switchs(by_groups, True):
            help = si.help  # @ReservedAssignment
            if si.list:
                help += "; may be given multiple times"
            if si.mandatory:
                help += "; required"
            if si.requires:
                help += "; requires %s" % (", ".join((("-" if len(s) == 1 else "--") + s) for s in si.requires))
            if si.excludes:
                help += "; excludes %s" % (", ".join((("-" if len(s) == 1 else "--") + s) for s in si.excludes))

            msg = indentation.join(wrapper.wrap(" ".join(l.strip() for l in help.splitlines())))

            if len(prefix) + wrapper.width >= cols:
                padding = indentation
            else:
                padding = " " * max(cols - wrapper.width - len(prefix) - 4, 1)
            print(description_indent % (prefix, padding, msg))

        if self._subcommands:
            print("Subcommands:")
            for name, subcls in sorted(self._subcommands.items()):
                subapp = subcls.get()
                doc = subapp.DESCRIPTION if subapp.DESCRIPTION else inspect.getdoc(subapp)
                help = doc + "; " if doc else ""  # @ReservedAssignment
                help += "see '%s %s --help' for more info" % (self.PROGNAME, name)

                msg = indentation.join(wrapper.wrap(" ".join(l.strip() for l in help.splitlines())))

                if len(name) + wrapper.width >= cols:
                    padding = indentation
                else:
                    padding = " " * max(cols - wrapper.width - len(name) - 4, 1)
                print(description_indent % (name, padding, msg))

    def _get_prog_version(self):
        ver = None
        curr = self
        while curr is not None:
            ver = getattr(curr, "VERSION", None)
            if ver is not None:
                return ver
            curr = curr.parent
        return ver

    @switch(["-v", "--version"], overridable = True, group = "Meta-switches")
    def version(self):
        """Prints the program's version and quits"""
        ver = self._get_prog_version()
        print ("%s %s" % (self.PROGNAME, ver if ver is not None else "(no version set)"))

