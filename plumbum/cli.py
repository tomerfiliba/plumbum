import sys
import inspect


class SwitchError(Exception):
    pass
class PositionalArgumentsError(SwitchError):
    pass
class SwitchCombinationError(SwitchError):
    pass
class UnknownSwitch(SwitchError):
    pass
class MissingArgument(SwitchError):
    pass
class MissingMandatorySwitch(SwitchError):
    pass
class WrongArgumentType(SwitchError):
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
        excludes = (), help = None, overridable = False, group = None):
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

class SwitchAttr(object):
    def __init__(self, names, argtype, **kwargs):
        switch(names, argtype = argtype, argname = "VALUE", **kwargs)(self)
        self._value = None
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

class ToggleAttr(SwitchAttr):
    def __init__(self, names, default = False, **kwargs):
        SwitchAttr.__init__(self, names, argtype = None, **kwargs)
        self._value = default
    def __call__(self, _, v):
        self._value = not self._value

def Flag(names, default = False, help = None):
    return ToggleAttr(names, default, help = help)

class CountAttr(SwitchAttr):
    def __init__(self, names, default = 0, **kwargs):
        SwitchAttr.__init__(self, names, argtype = None, list = True, **kwargs)
        self._value = default
    def __call__(self, _, v):
        self._value = len(v)

#===================================================================================================
# switch type validators
#===================================================================================================
class Range(object):
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

class Enum(object):
    def __init__(self, *values):
        self.values = values
    def __repr__(self):
        return "Enum(%s)" % (", ".join(self.values))
    def __call__(self, obj):
        if obj not in self.values:
            raise ValueError("Expected one of %r" % (self.values,))
        return obj


#===================================================================================================
# CLI Application base class
#===================================================================================================
class Application(object):
    PROGNAME = None
    DESCRIPTION = None
    VERSION = "0.1"
    USAGE = "Usage: %(executable)s [SWITCHES] %(tailargs)s"
    
    def __init__(self, executable):
        if self.PROGNAME is None:
            self.PROGNAME = executable
        self.executable = executable
        self._switches_by_name = {}
        self._switches_by_func = {}
        for cls in reversed(self.__class__.mro()):
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
        while argv:
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
                except (TypeError, ValueError) as ex:
                    raise WrongArgumentType("Argument of %s expected to be %r, not %r:\n    %r" % (
                        swname, swinfo.argtype, val, ex))
            else:
                val = None
            if swinfo.func in swfuncs:
                if swinfo.list:
                    swfuncs[swinfo.func][1].append(val)
                else:
                    raise SwitchError("cannot repeat %r")
            else:
                if swinfo.list:
                    swfuncs[swinfo.func] = (swname, [val])
                else:
                    swfuncs[swinfo.func] = (swname, val)
        
        if self.help.im_func in swfuncs:
            raise ShowHelp()
        if self.version.im_func in swfuncs:
            raise ShowVersion()
        
        requirements = {}
        exclusions = {}
        for swinfo in self._switches_by_func.values():
            if swinfo.mandatory and not swinfo.func in swfuncs:
                raise MissingMandatorySwitch("Switch %s is mandatory" % 
                    ("/".join(("-" if len(n) == 1 else "--") + n for n in swinfo.names),))
            requirements[swinfo.func] = set(self._switches_by_name[req] for req in swinfo.requires)
            exclusions[swinfo.func] = set(self._switches_by_name[exc] for exc in swinfo.excludes)
        
        gotten = set(swfuncs.keys())
        for func in gotten:
            missing = requirements[func] - gotten
            if missing:
                raise SwitchCombinationError("Given %s, the following are missing %r" % 
                    (swfuncs[func][0], [swfuncs[f] for f in missing]))
            invalid = exclusions[func] & gotten
            if invalid:
                raise SwitchCombinationError("Given %s, the following are invalid %r" % 
                    (swfuncs[func][0], [swfuncs[f] for f in invalid]))
        
        m_args, m_varargs, _, m_defaults = inspect.getargspec(self.main)
        max_args = sys.maxint if m_varargs else len(m_args) - 1
        min_args = len(m_args) - 1 - (len(m_defaults) if m_defaults else 0)
        if len(tailargs) < min_args:
            raise PositionalArgumentsError("Expected at least %d positional arguments, got %r" % 
                (min_args, tailargs))
        elif len(tailargs) > max_args:
            raise PositionalArgumentsError("Expected at most %d positional arguments, got %r" % 
                (max_args, tailargs))
        
        return swfuncs, tailargs
    
    @classmethod
    def run(cls, argv = sys.argv):
        argv = list(argv)
        inst = cls(argv.pop(0))
        try:
            swfuncs, tailargs = inst._parse_args(list(argv))
        except ShowHelp:
            inst.help()
            sys.exit(0)
        except ShowVersion:
            inst.version()
            sys.exit(0)
        except SwitchError, ex:
            print ex
            print
            inst.help()
            sys.exit(1)
        for f, (_, a) in swfuncs.items():
            if a is None:
                f(inst)
            else:
                f(inst, a)
        retcode = inst.main(*tailargs)
        sys.exit(retcode)
    
    def main(self):
        pass
    
    @switch(["-h", "--help"], overridable = True, group = "Meta-switches")
    def help(self): #@ReservedAssignment
        """Prints this help message and quits"""
        self.version()
        if self.DESCRIPTION:
            print self.DESCRIPTION.strip()

        m_args, m_varargs, _, m_defaults = inspect.getargspec(self.main)
        tailargs = m_args[1:] # skip self
        if m_defaults:
            for d, i in enumerate(reversed(m_defaults)):
                tailargs[-i] = "[%s=%r]" % (tailargs[-i], d)
        if m_varargs:
            tailargs.append("%s..." % (m_varargs,))
        tailargs = " ".join(tailargs)
        
        print
        print self.USAGE % {"executable" : self.executable, "progname" : self.PROGNAME, 
            "tailargs" : tailargs} 
        
        by_groups = {}
        for si in self._switches_by_func.values():
            if si.group not in by_groups:
                by_groups[si.group] = []
            by_groups[si.group].append(si)
        
        for grp, swinfos in sorted(by_groups.items(), key = lambda item: item[0]):
            if grp is None:
                print "Switches:"
            if grp is not None:
                print "%s:" % (grp,)
            
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
                print "    %-25s  %s" % (swnames + argtype, help)
            print
    
    @switch(["-v", "--version"], overridable = True, group = "Meta-switches")
    def version(self):
        """Prints the program's version and quits"""
        print self.PROGNAME, "v" + self.VERSION



#===================================================================================================
# test
#===================================================================================================
#if __name__ == "__main__":
#    class Test(Application):
#        @switch(["a"])
#        def spam(self):
#            print "!!a"
#
#        @switch(["b", "bacon"], argtype=int, mandatory = True)
#        def bacon(self, param):
#            print "!!b", param
#        
#        eggs = SwitchAttr(["e"], str, help = "sets the eggs attribute")
#        verbose = CountAttr(["v"], help = "increases the verbosity level")
#        
#        def main(self, *args):
#            print args
#            print "vebosity =", self.verbose
#            print "eggs =", self.eggs
#    
#    Test.run(["foo", "--bacon=81", "-a", "-v", "-e", "7", "-vv", "--", "lala", "-e", "7"])
#    #Test.run(["foo", "-h"])





