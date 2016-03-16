from __future__ import division, print_function, absolute_import
import os
import sys
import functools
from textwrap import TextWrapper
from collections import defaultdict

from plumbum.lib import six, getdoc
from plumbum.cli.terminal import get_terminal_size
from plumbum.cli.switches import (SwitchError, UnknownSwitch, MissingArgument, WrongArgumentType,
    MissingMandatorySwitch, SwitchCombinationError, PositionalArgumentsError, switch,
    SubcommandError, Flag, CountOf)
from plumbum import colors, local


class ShowHelp(SwitchError):
    pass
class ShowHelpAll(SwitchError):
    pass
class ShowVersion(SwitchError):
    pass

class SwitchParseInfo(object):
    __slots__ = ["swname", "val", "index", "__weakref__"]
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
      name of the executable (``argv[0]``), can be in color. If only a color, will be applied to the name.

    * ``VERSION`` - the program's version (defaults to ``1.0``, can be in color)

    * ``DESCRIPTION`` - a short description of your program (shown in help). If not set,
      the class' ``__doc__`` will be used. Can be in color.

    * ``USAGE`` - the usage line (shown in help)

    * ``COLOR_USAGE`` - The color of the usage line

    * ``COLOR_GROUPS`` - A dictionary that sets colors for the groups, like Meta-switches, Switches,
      and Subcommands

    * ``SUBCOMMAND_HELPMSG`` - Controls the printing of extra "see subcommand -h" help message.
      Default is a message, set to false to remove.

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
    COLOR_USAGE = None
    COLOR_GROUPS = None
    CALL_MAIN_IF_NESTED_COMMAND = True
    SUBCOMMAND_HELPMSG = "see '{parent} {sub} --help' for more info"

    parent = None
    nested_command = None
    _unbound_switches = ()

    def __new__(cls, executable=None):
        """Allows running the class directly as a shortcut for main.
        This is neccisary for some setup scripts that want a single function,
        instead of an expression with a dot in it."""


        if executable is None:
            return cls.run()
            # This return value was not a class instance, so __init__ is never called
        else:
            return super(Application, cls).__new__(cls)

    def __init__(self, executable):
        # Filter colors

        if self.PROGNAME is None:
            self.PROGNAME = os.path.basename(executable)
        elif isinstance(self.PROGNAME, colors._style):
            self.PROGNAME = self.PROGNAME | os.path.basename(executable)
        elif colors.filter(self.PROGNAME) == '':
            self.PROGNAME = colors.extract(self.PROGNAME) | os.path.basename(executable)
        if self.DESCRIPTION is None:
            self.DESCRIPTION = getdoc(self)

        # Allow None for the colors
        self.COLOR_GROUPS=defaultdict(lambda:colors.do_nothing, dict() if type(self).COLOR_GROUPS is None else type(self).COLOR_GROUPS )
        if type(self).COLOR_USAGE is None:
            self.COLOR_USAGE=colors.do_nothing

        self.executable = executable
        self._switches_by_name = {}
        self._switches_by_func = {}
        self._switches_by_envar = {}
        self._subcommands = {}

        for cls in reversed(type(self).mro()):
            for obj in cls.__dict__.values():
                if isinstance(obj, Subcommand):
                    name = colors.filter(obj.name)
                    if name.startswith("-"):
                        raise SubcommandError("Subcommand names cannot start with '-'")
                    # it's okay for child classes to override subcommands set by their parents
                    self._subcommands[name] = obj
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
                    if swinfo.envname:
                        self._switches_by_envar[swinfo.envname] = swinfo


    @property
    def root_app(self):
        return self.parent.root_app if self.parent else self

    @classmethod
    def unbind_switches(cls, *switch_names):
        """Unbinds the given switch names from this application. For example

        ::

            class MyApp(cli.Application):
                pass
            MyApp.unbind_switches("--version")

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
            val = None
            if a == "--":
                # end of options, treat the rest as tailargs
                tailargs.extend(argv)
                break

            if a in self._subcommands:
                subcmd = self._subcommands[a].get()
                self.nested_command = (subcmd, [self.PROGNAME + " " + self._subcommands[a].name] + argv)
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
            val = self._handle_argument(val, swinfo.argtype, name)

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

        # Extracting arguments from environment variables
        envindex = 0
        for env, swinfo in self._switches_by_envar.items():
            envindex -= 1
            envval = local.env.get(env)
            if envval is None:
                continue

            if swinfo.func in swfuncs:
                continue  # skip if overridden by command line arguments

            val = self._handle_argument(envval, swinfo.argtype, env)
            envname = "$%s" % (env,)
            if swinfo.list:
                # multiple values over environment variables are not supported,
                # this will require some sort of escaping and separator convention
                swfuncs[swinfo.func] = SwitchParseInfo(envname, ([val],), envindex)
            elif val is NotImplemented:
                swfuncs[swinfo.func] = SwitchParseInfo(envname, (), envindex)
            else:
                swfuncs[swinfo.func] = SwitchParseInfo(envname, (val,), envindex)

        return swfuncs, tailargs

    @classmethod
    def autocomplete(cls, argv):
        """This is supplied to make subclassing and testing argument completion methods easier"""
        pass

    @staticmethod
    def _handle_argument(val, argtype, name):
        if argtype:
            try:
                return argtype(val)
            except (TypeError, ValueError):
                ex = sys.exc_info()[1]  # compat
                raise WrongArgumentType("Argument of %s expected to be %r, not %r:\n    %r" % (
                    name, argtype, val, ex))
        else:
            return NotImplemented

    def _validate_args(self, swfuncs, tailargs):
        if six.get_method_function(self.help) in swfuncs:
            raise ShowHelp()
        if six.get_method_function(self.helpall) in swfuncs:
            raise ShowHelpAll()
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

        m = six.getfullargspec(self.main)
        max_args = six.MAXSIZE if m.varargs else len(m.args) - 1
        min_args = len(m.args) - 1 - (len(m.defaults) if m.defaults else 0)
        if len(tailargs) < min_args:
            raise PositionalArgumentsError("Expected at least %d positional arguments, got %r" %
                (min_args, tailargs))
        elif len(tailargs) > max_args:
            raise PositionalArgumentsError("Expected at most %d positional arguments, got %r" %
                (max_args, tailargs))

        # Positional arguement validataion
        if hasattr(self.main, 'positional'):
            tailargs = self._positional_validate(tailargs, self.main.positional, self.main.positional_varargs, m.args[1:], m.varargs)

        elif hasattr(m, 'annotations'):
            args_names = list(m.args[1:])
            positional = [None]*len(args_names)
            varargs = None


             # All args are positional, so convert kargs to positional
            for item in m.annotations:
                if item == m.varargs:
                    varargs = m.annotations[item]
                else:
                    positional[args_names.index(item)] = m.annotations[item]

            tailargs = self._positional_validate(tailargs, positional, varargs,
                                                 m.args[1:], m.varargs)

        ordered = [(f, a) for _, f, a in
            sorted([(sf.index, f, sf.val) for f, sf in swfuncs.items()])]
        return ordered, tailargs

    def _positional_validate(self, args, validator_list, varargs, argnames, varargname):
        """Makes sure args follows the validation given input"""
        out_args = list(args)

        for i in range(min(len(args),len(validator_list))):

            if validator_list[i] is not None:
                out_args[i] = self._handle_argument(args[i], validator_list[i], argnames[i])

        if len(args) > len(validator_list):
            if varargs is not None:
                out_args[len(validator_list):] = [
                    self._handle_argument(a, varargs, varargname) for a in args[len(validator_list):]]
            else:
                out_args[len(validator_list):] = args[len(validator_list):]

        return out_args

    @classmethod
    def run(cls, argv = None, exit = True):  # @ReservedAssignment
        """
        Runs the application, taking the arguments from ``sys.argv`` by default if
        nothing is passed. If ``exit`` is
        ``True`` (the default), the function will exit with the appropriate return code;
        otherwise it will return a tuple of ``(inst, retcode)``, where ``inst`` is the
        application instance created internally by this function and ``retcode`` is the
        exit code of the application.

        .. note::
           Setting ``exit`` to ``False`` is intendend for testing/debugging purposes only -- do
           not override it other situations.
        """
        if argv is None:
            argv = sys.argv
        cls.autocomplete(argv)
        argv = list(argv)
        inst = cls(argv.pop(0))
        retcode = 0
        try:
            swfuncs, tailargs = inst._parse_args(argv)
            ordered, tailargs = inst._validate_args(swfuncs, tailargs)
        except ShowHelp:
            inst.help()
        except ShowHelpAll:
            inst.helpall()
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

            cleanup = None
            if not inst.nested_command or inst.CALL_MAIN_IF_NESTED_COMMAND:
                retcode = inst.main(*tailargs)
                cleanup = functools.partial(inst.cleanup, retcode)
            if not retcode and inst.nested_command:
                subapp, argv = inst.nested_command
                subapp.parent = inst
                inst, retcode = subapp.run(argv, exit = False)

            if cleanup:
                cleanup()

            if retcode is None:
                retcode = 0

        if exit:
            sys.exit(retcode)
        else:
            return inst, retcode

    @classmethod
    def invoke(cls, *args, **switches):
        """Invoke this application programmatically (as a function), in the same way ``run()``
        would. There are two key differences: the return value of ``main()`` is not converted to
        an integer (returned as-is), and exceptions are not swallowed either.

        :param args: any positional arguments for ``main()``
        :param switches: command-line switches are passed as keyword arguments,
                         e.g., ``foo=5`` for ``--foo=5``
        """

        inst = cls("")

        swfuncs = inst._parse_kwd_args(switches)
        ordered, tailargs = inst._validate_args(swfuncs, args)
        for f, a in ordered:
            f(inst, *a)

        cleanup = None
        if not inst.nested_command or inst.CALL_MAIN_IF_NESTED_COMMAND:
            retcode = inst.main(*tailargs)
            cleanup = functools.partial(inst.cleanup, retcode)
        if not retcode and inst.nested_command:
            subapp, argv = inst.nested_command
            subapp.parent = inst
            inst, retcode = subapp.run(argv, exit = False)

        if cleanup:
            cleanup()

        return inst, retcode

    def _parse_kwd_args(self, switches):
        """Parses keywords (positional arguments), used by invoke."""
        swfuncs = {}
        for index, (swname, val) in enumerate(switches.items(), 1):
            switch = getattr(type(self), swname)
            swinfo = self._switches_by_func[switch._switch_info.func]
            if isinstance(switch, CountOf):
                p = (range(val),)
            elif swinfo.list and not hasattr(val, "__iter__"):
                raise SwitchError("Switch %r must be a sequence (iterable)" % (swname,))
            elif not swinfo.argtype:
                # a flag
                if val not in (True, False, None, Flag):
                    raise SwitchError("Switch %r is a boolean flag" % (swname,))
                p = ()
            else:
                p = (val,)
            swfuncs[swinfo.func] = SwitchParseInfo(swname, p, index)
        return swfuncs

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

    def cleanup(self, retcode):
        """Called after ``main()`` and all subapplications have executed, to perform any necessary cleanup.

        :param retcode: the return code of ``main()``
        """

    @switch(["--help-all"], overridable = True, group = "Meta-switches")
    def helpall(self):
        """Print help messages of all subcommands and quit"""
        self.help()
        print("")

        if self._subcommands:
            for name, subcls in sorted(self._subcommands.items()):
                subapp = (subcls.get())("%s %s" % (self.PROGNAME, name))
                subapp.parent = self
                for si in subapp._switches_by_func.values():
                    if si.group == "Meta-switches":
                        si.group = "Hidden-switches"
                subapp.helpall()

    @switch(["-h", "--help"], overridable = True, group = "Meta-switches")
    def help(self):  # @ReservedAssignment
        """Prints this help message and quits"""
        if self._get_prog_version():
            self.version()
            print("")
        if self.DESCRIPTION:
            print(self.DESCRIPTION.strip() + '\n')

        m = six.getfullargspec(self.main)
        tailargs = m.args[1:]  # skip self
        if m.defaults:
            for i, d in enumerate(reversed(m.defaults)):
                tailargs[-i - 1] = "[%s=%r]" % (tailargs[-i - 1], d)
        if m.varargs:
            tailargs.append("%s..." % (m.varargs,))
        tailargs = " ".join(tailargs)

        with self.COLOR_USAGE:
            print("Usage:")
            if not self.USAGE:
                if self._subcommands:
                    self.USAGE = "    %(progname)s [SWITCHES] [SUBCOMMAND [SWITCHES]] %(tailargs)s\n"
                else:
                    self.USAGE = "    %(progname)s [SWITCHES] %(tailargs)s\n"
            print(self.USAGE % {"progname": colors.filter(self.PROGNAME), "tailargs": tailargs})

        by_groups = {}
        for si in self._switches_by_func.values():
            if si.group not in by_groups:
                by_groups[si.group] = []
            by_groups[si.group].append(si)

        def switchs(by_groups, show_groups):
            for grp, swinfos in sorted(by_groups.items(), key = lambda item: item[0]):
                if show_groups:
                    print(self.COLOR_GROUPS[grp] | grp)

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
                    yield si, prefix, self.COLOR_GROUPS[grp]

                if show_groups:
                    print("")

        sw_width = max(len(prefix) for si, prefix, color in switchs(by_groups, False)) + 4
        cols, _ = get_terminal_size()
        description_indent = "    %s%s%s"
        wrapper = TextWrapper(width = max(cols - min(sw_width, 60), 50) - 6)
        indentation = "\n" + " " * (cols - wrapper.width)

        for si, prefix, color in switchs(by_groups, True):
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
            print(description_indent % (color | prefix, padding, color | msg))

        if self._subcommands:
            gc = self.COLOR_GROUPS["Subcommands"]
            print(gc | "Subcommands:")
            for name, subcls in sorted(self._subcommands.items()):
                with gc:
                    subapp = subcls.get()
                    doc = subapp.DESCRIPTION if subapp.DESCRIPTION else getdoc(subapp)
                    if self.SUBCOMMAND_HELPMSG:
                        help = doc + "; " if doc else ""  # @ReservedAssignment
                        help += self.SUBCOMMAND_HELPMSG.format(parent=self.PROGNAME, sub=name)
                    else:
                        help = doc if doc else "" # @ReservedAssignment

                    msg = indentation.join(wrapper.wrap(" ".join(l.strip() for l in help.splitlines())))

                    if len(name) + wrapper.width >= cols:
                        padding = indentation
                    else:
                        padding = " " * max(cols - wrapper.width - len(name) - 4, 1)
                    if colors.contains_colors(subcls.name):
                        bodycolor = colors.extract(subcls.name)
                    else:
                        bodycolor = gc

                    print(description_indent
                            % (subcls.name, padding,
                               bodycolor | colors.filter(msg)))



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
        ver_name = ver if ver is not None else "(version not set)"
        print('{0} {1}'.format(self.PROGNAME, ver_name))

