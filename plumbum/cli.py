import sys
import six
import inspect
from plumbum import local


class SwitchError(Exception):
    """A general switch related-error (base class of all other switch errors)"""
    pass
class PositionalArgumentsError(SwitchError):
    """Raised when an invalid number of positional arguments has been given"""
    pass
class SwitchCombinationError(SwitchError):
    """Raised when an invalid combination of switches has been given"""
    pass
class UnknownSwitch(SwitchError):
    """Raised when an unrecognized switch has been given"""
    pass
class MissingArgument(SwitchError):
    """Raised when a switch requires an argument, but one was not provided"""
    pass
class MissingMandatorySwitch(SwitchError):
    """Raised when a mandatory switch has not been given"""
    pass
class WrongArgumentType(SwitchError):
    """Raised when a switch expected an argument of some type, but an argument of a wrong
    type has been given"""
    pass
class ShowHelp(SwitchError):
    pass
class ShowVersion(SwitchError):
    pass

#===================================================================================================
# The switch decorator
#===================================================================================================
class SwitchInfo(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def switch(names, argtype = None, argname = None, list = False, mandatory = False, requires = (), 
        excludes = (), help = None, overridable = False, group = "Switches"):
    """
    A decorator that exposes functions as command-line switches. Usage::
    
        class MyApp(Application):
            @switch(["-l", "--log-to-file"], argtype = str)
            def log_to_file(self, filename):
                handler = logging.FileHandler(filename)
                logger.addHandler(handler)
            
            @switch(["--verbose"], excludes=["--terse"], requires=["--log-to-file"])
            def set_debug(self):
                logger.setLevel(logging.DEBUG)

            @switch(["--terse"], excludes=["--verbose"], requires=["--log-to-file"])
            def set_terse(self):
                logger.setLevel(logging.WARNING)
    
    :param names: The name(s) under which the function is reachable; it can be a string
                  or a list of string, but at least one name is required. There's no need
                  to prefix the name with ``-`` or ``--`` (this is added automatically),
                  but it can be used for clarity. Single-letter names are prefixed by ``-``,
                  while longer names are prefixed by ``--``
    
    :param argtype: If this function takes an argument, you need to specify its type. The
                    default is ``None``, which means the function takes no argument. The type
                    is more of a "validator" than a real type; it can be any callable object
                    that raises a ``TypeError`` if the argument is invalid, or returns an
                    appropriate value on success. If the user provides an invalid value, 
                    :func:`plumbum.cli.WrongArgumentType`
    
    :param argname: The name of the argument; if ``None``, the name will be inferred from the
                    function's signature
    
    :param list: Whether or not this switch can be repeated (e.g. ``gcc -I/lib -I/usr/lib``).
                 If ``False``, only a single occurrence of the switch is allowed; if ``True``,
                 it may be repeated indefinitely. The occurrences are collected into a list,
                 so the function is only called once with the collections. For instance,
                 for ``gcc -I/lib -I/usr/lib``, the function will be called with 
                 ``["/lib", "/usr/lib"]``.
    
    :param mandatory: Whether or not this switch is mandatory; if a mandatory switch is not
                      given, :class:`MissingMandatorySwitch <plumbum.cli.MissingMandatorySwitch>`
                      is raised. The default is ``False``.
    
    :param requires: A list of switches that this switch depends on ("requires"). This means that 
                     it's invalid to invoke this switch without also invoking the required ones. 
                     In the example above, it's illegal to pass ``--verbose`` or ``--terse`` 
                     without also passing ``--log-to-file``. By default, this list is empty, 
                     which means the switch has no prerequisites. If an invalid combination
                     is given, :class:`SwitchCombinationError <plumbum.cli.SwitchCombinationError>`
                     is raised.
                     
                     Note that this list is made of the switch *names*; if a switch has more 
                     than a single name, any of its names will do.
                     
                     .. note::
                        There is no guarantee on the (topological) order in which the actual 
                        switch functions will be invoked, as the dependency graph might contain
                        cycles.
    
    :param excludes: A list of switches that this switch forbids ("excludes"). This means that 
                     it's invalid to invoke this switch if any of the excluded ones are given. 
                     In the example above, it's illegal to pass ``--verbose`` along with 
                     ``--terse``, as it will result in a contradiction. By default, this list 
                     is empty, which means the switch has no prerequisites. If an invalid 
                     combination is given, :class:`SwitchCombinationError 
                     <plumbum.cli.SwitchCombinationError>` is raised.
                     
                     Note that this list is made of the switch *names*; if a switch has more 
                     than a single name, any of its names will do.
    
    :param help: The help message (description) for this switch; this description is used when
                 ``--help`` is given. If ``None``, the function's docstring will be used.
    
    :param overridable: Whether or not the names of this switch are overridable by other switches.
                        If ``False`` (the default), having another switch function with the same 
                        name(s) will cause an exception. If ``True``, this is silently ignored.
    
    :param group: The switch's *group*; this is a string that is used to group related switches
                  together when ``--help`` is given. The default group is ``Switches``.
    
    :returns: The decorated function (with a ``_switch_info`` attribute)
    """
    if isinstance(names, str):
        names = [names]
    names = [n.lstrip("-") for n in names]
    requires = [n.lstrip("-") for n in requires]
    excludes = [n.lstrip("-") for n in excludes]
    
    def deco(func):
        if argname is None:
            argspec = inspect.getargspec(func)[0]
            if len(argspec) == 2:
                argname2 = argspec[1]
            else:
                argname2 = "VALUE"
        else:
            argname2 = argname
        help2 = inspect.getdoc(func) if help is None else help
        if not help2:
            help2 = str(func)
        func._switch_info = SwitchInfo(names = names, argtype = argtype, list = list, func = func, 
            mandatory = mandatory, overridable = overridable, group = group,
            requires = requires, excludes = excludes, argname = argname2, help = help2)
        return func
    return deco

def autoswitch(*args, **kwargs):
    """A decorator that exposes a function as a switch, "inferring" the name of the switch
    from the function's name (converting to lower-case, and replacing underscores by hyphens).
    The arguments are the same as for :func:`switch <plumbum.cli.switch>`."""
    def deco(func):
        return switch(func.__name__.replace("_", "-"), *args, **kwargs)(func)
    return deco

#===================================================================================================
# Switch Attributes
#===================================================================================================
class SwitchAttr(object):
    """
    A switch that stores its result in an attribute (descriptor). Usage::
    
        class MyApp(Application):
            logfile = SwitchAttr(["-f", "--log-file"], str)
            
            def main(self):
                if self.logfile:
                    open(self.logfile, "w")
    
    :param names: The switch names
    :param argtype: The switch argument's (and attribute's) type
    :param default: The attribute's default value (``None``)
    :param kwargs: Any of the keyword arguments accepted by :func:`switch <plumbum.cli.switch>`
    """
    def __init__(self, names, argtype, default = None, **kwargs):
        self.__doc__ = "Sets an attribute" # to prevent the help message from showing SwitchAttr's docstring
        switch(names, argtype = argtype, argname = "VALUE", **kwargs)(self)
        self._value = default
    def __call__(self, _, val):
        self._value = val
    def __get__(self, cls, inst):
        if inst is None:
            return self
        else:
            return self._value
    def __set__(self, cls, inst, val):
        if inst is None:
            raise AttributeError("cannot set an unbound SwitchAttr")
        else:
            self._value = val

class Flag(SwitchAttr):
    """A specialized :class:`SwitchAttr <plumbum.cli.SwitchAttr>` for boolean flags. If the flag is not
    given, the value of this attribute is the ``default``; if it is given, the value changes
    to ``not default``. Usage::
    
        class MyApp(Application):
            verbose = Flag(["-v", "--verbose"], help = "If given, I'll be very talkative")

    :param names: The switch names
    :param default: The attribute's initial value (``False`` by default)
    :param kwargs: Any of the keyword arguments accepted by :func:`switch <plumbum.cli.switch>`,
                   except for ``list`` and ``argtype``.
    """
    def __init__(self, names, default = False, **kwargs):
        SwitchAttr.__init__(self, names, argtype = None, default = default, list = False, **kwargs)
    def __call__(self, _):
        self._value = not self._value

class CountingAttr(SwitchAttr):
    """A specialized :class:`SwitchAttr <plumbum.cli.SwitchAttr>` that counts the number of 
    occurrences of the switch in the command line. Usage::

        class MyApp(Application):
            verbosity = CountingAttr(["-v", "--verbose"], help = "The more, the merrier")
            
    If ``-v -v -vv`` is given in the command-line, it will result in ``verbosity = 4``.
    
    :param names: The switch names
    :param default: The default value (0)
    :param kwargs: Any of the keyword arguments accepted by :func:`switch <plumbum.cli.switch>`,
                   except for ``list`` and ``argtype``.
    """
    def __init__(self, names, default = 0, **kwargs):
        SwitchAttr.__init__(self, names, argtype = None, default = default, list = True, **kwargs)
    def __call__(self, _, v):
        self._value = len(v)

#===================================================================================================
# Switch type validators
#===================================================================================================
class Range(object):
    """
    A switch-type validator that checks for the inclusion of a value in a certain range. 
    Usage::
    
        class MyApp(Application):
            age = SwitchAttr(["--age"], Range(18, 120))
    
    :param start: The minimal value
    :param end: The maximal value
    """
    def __init__(self, start, end):
        self.start = start
        self.end = end
    def __repr__(self):
        return "[%d..%d]" % (self.start, self.end)
    def __call__(self, obj):
        obj = int(obj)
        if obj < self.start or obj > self.end:
            raise ValueError("Not in range [%d..%d]" % (self.start, self.end))
        return obj

class Set(object):
    """
    A switch-type validator that checks that the value is contained in a defined 
    set of values. Usage::
    
        class MyApp(Application):
            mode = SwitchAttr(["--mode"], Set("TCP", "UDP", case_insensitive = False))
    
    :param values: The set of values (strings)
    :param case_insensitive: A keyword argument that indicates whether to use case-sensitive
                             comparison or not. The default is ``True``
    """
    def __init__(self, *values, **kwargs):
        self.case_sensitive = kwargs.pop("case_sensitive", False)
        if kwargs:
            raise TypeError("got unexpected keyword argument(s)", kwargs.keys())
        self.values = dict(((v if self.case_sensitive else v.lower()), v) for v in values)
    def __repr__(self):
        return "Set(%s)" % (", ".join(repr(v) for v in self.values.values()))
    def __call__(self, obj):
        if not self.case_sensitive:
            obj = obj.lower()
        if obj not in self.values:
            raise ValueError("Expected one of %r" % (list(self.values.values()),))
        return self.values[obj]

class Predicate(object):
    def __str__(self):
        return self.__class__.__name__

class ExistingDirectory(Predicate):
    """A switch-type validator that ensures that the given argument is an existing directory"""
    def __call__(self, val):
        p = local.path(val)
        if not p.isdir():
            raise ValueError("%r is not a directory" % (val,))
        return p
ExistingDirectory = ExistingDirectory()

class ExistingFile(Predicate):
    """A switch-type validator that ensures that the given argument is an existing file"""
    def __call__(self, val):
        p = local.path(val)
        if not p.isfile():
            raise ValueError("%r is not a file" % (val,))
        return p
ExistingFile = ExistingFile()

class NonexistentPath(Predicate):
    """A switch-type validator that ensures that the given argument is an nonexistent path"""
    def __call__(self, val):
        p = local.path(val)
        if not p.exists():
            raise ValueError("%r already exists" % (val,))
        return p
NonexistentPath = NonexistentPath()


#===================================================================================================
# CLI Application base class
#===================================================================================================
class NoArg(object):
    pass

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
    
    * ``DESCRIPTION`` - a short description of your program (shown in help)
    
    * ``USAGE`` - the usage line (shown in help)
    """
    
    PROGNAME = None
    DESCRIPTION = None
    VERSION = "1.0"
    USAGE = "Usage: %(executable)s [SWITCHES] %(tailargs)s"
    
    def __init__(self, executable):
        if self.PROGNAME is None:
            self.PROGNAME = executable
        self.executable = executable
        self._switches_by_name = {}
        self._switches_by_func = {}
        for cls in reversed(type(self).mro()):
            for obj in cls.__dict__.values():
                swinfo = getattr(obj, "_switch_info", None)
                if not swinfo:
                    continue
                for name in swinfo.names:
                    if name in self._switches_by_name and not self._switches_by_name[name].overridable:
                        raise SwitchError("Switch %r already defined and is not overridable" % (name,))
                    self._switches_by_name[name] = swinfo
                self._switches_by_func[swinfo.func] = swinfo
    
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
                    if a[0] == "=":
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
                    ex = sys.exc_info()[1] # compat
                    raise WrongArgumentType("Argument of %s expected to be %r, not %r:\n    %r" % (
                        swname, swinfo.argtype, val, ex))
            else:
                val = NoArg
            
            if swinfo.func in swfuncs:
                if swinfo.list:
                    swfuncs[swinfo.func][1].append(val)
                else:
                    raise SwitchError("cannot repeat %r")
            else:
                if swinfo.list:
                    swfuncs[swinfo.func] = (swname, [val], index)
                else:
                    swfuncs[swinfo.func] = (swname, val, index)
        
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
                    (swfuncs[func][0], [self._switches_by_func[f].names[0] for f in missing]))
            invalid = set(f.func for f in exclusions[func]) & gotten
            if invalid:
                raise SwitchCombinationError("Given %s, the following are invalid %r" % 
                    (swfuncs[func][0], [swfuncs[f][0] for f in invalid]))
        
        m_args, m_varargs, _, m_defaults = inspect.getargspec(self.main)
        max_args = six.MAXSIZE if m_varargs else len(m_args) - 1
        min_args = len(m_args) - 1 - (len(m_defaults) if m_defaults else 0)
        if len(tailargs) < min_args:
            raise PositionalArgumentsError("Expected at least %d positional arguments, got %r" % 
                (min_args, tailargs))
        elif len(tailargs) > max_args:
            raise PositionalArgumentsError("Expected at most %d positional arguments, got %r" % 
                (max_args, tailargs))
        
        ordered = [x for _, x in sorted(
                (index, (f, () if a is NoArg else (a,))) 
                    for f, (_, a, index) in swfuncs.items())]
        return ordered, tailargs
    
    @classmethod
    def _run(cls, argv):
        argv = list(argv)
        inst = cls(argv.pop(0))
        try:
            ordered, tailargs = inst._parse_args(list(argv))
        except ShowHelp:
            inst.help()
            return inst, 0
        except ShowVersion:
            inst.version()
            return inst, 0
        except SwitchError:
            ex = sys.exc_info()[1] # compatibility with python 2.5
            print(ex)
            print("")
            inst.help()
            return inst, 1
        
        for f, a in ordered:
            f(inst, *a)
        retcode = inst.main(*tailargs)
        if retcode is None:
            retcode = 0
        return inst, retcode
    
    @classmethod
    def run(cls, argv = sys.argv):
        """Runs the application, taking the arguments from ``sys.argv``, and exiting with the
        appropriate exit code; this function does not return"""
        _, retcode = cls._run(argv)
        sys.exit(retcode)
    
    def main(self):
        """Override me"""
        pass
    
    @switch(["-h", "--help"], overridable = True, group = "Meta-switches")
    def help(self): #@ReservedAssignment
        """Prints this help message and quits"""
        self.version()
        if self.DESCRIPTION:
            print(self.DESCRIPTION.strip())

        m_args, m_varargs, _, m_defaults = inspect.getargspec(self.main)
        tailargs = m_args[1:] # skip self
        if m_defaults:
            for i, d in enumerate(reversed(m_defaults)):
                tailargs[-i - 1] = "[%s=%r]" % (tailargs[-i - 1], d)
        if m_varargs:
            tailargs.append("%s..." % (m_varargs,))
        tailargs = " ".join(tailargs)
        
        print("")
        print(self.USAGE % {"executable" : self.executable, "progname" : self.PROGNAME, 
            "tailargs" : tailargs}) 
        
        by_groups = {}
        for si in self._switches_by_func.values():
            if si.group not in by_groups:
                by_groups[si.group] = []
            by_groups[si.group].append(si)
        
        for grp, swinfos in sorted(by_groups.items(), key = lambda item: item[0]):
            print("%s:" % (grp,))
            
            for si in sorted(swinfos, key = lambda si: si.names):
                swnames = ", ".join(("-" if len(n) == 1 else "--") + n for n in si.names 
                    if self._switches_by_name[n] == si)
                if si.argtype:
                    if isinstance(si.argtype, type):
                        typename = si.argtype.__name__
                    else:
                        typename = str(si.argtype)
                    argtype = " %s:%s" % (si.argname.upper(), typename)
                else:
                    argtype = ""
                help = si.help #@ReservedAssignment
                if si.list:
                    help += "; may be given multiple times"
                if si.mandatory:
                    help += "; required"
                if si.requires:
                    help += "; requires %s" % (", ".join(si.requires))
                if si.excludes:
                    help += "; excludes %s" % (", ".join(si.excludes))
                print("    %-25s  %s" % (swnames + argtype, help))
            print ("")
    
    @switch(["-v", "--version"], overridable = True, group = "Meta-switches")
    def version(self):
        """Prints the program's version and quits"""
        print ("%s v%s" % (self.PROGNAME, self.VERSION))



