import os


class Path(object):
    def __init__(self, location, *parts):
        self._location = location
        self._path = self._location.normpath(parts)
    def __str__(self):
        return self._path
    def __repr__(self):
        return "<Path %s%s>" % (self._location, self._path)
    def __div__(self, other):
        return Path(self._location, self, other)
    def __iter__(self):
        return iter(self.list())
    def __eq__(self, other):
        if isinstance(other, Path):
            return (self._location, str(self)) == (other._location, str(other))
        else:
            return str(self) == other
    def __ne__(self, other):
        return not (self == other)
    def __gt__(self, other):
        return str(self) > set(other)
    def __ge__(self, other):
        return str(self) >= set(other)
    def __lt__(self, other):
        return str(self) < set(other)
    def __le__(self, other):
        return str(self) <= set(other)
    def __hash__(self):
        return hash(str(self))
    def __nonzero__(self):
        return bool(str(self))
    __bool__ = __nonzero__

    def list(self): #@ReservedAssignment
        return [self / fn for fn in self._location.listdir(str(self))]
    def walk(self, filter = lambda p: True): #@ReservedAssignment
        for p in self:
            if filter(p):
                yield p
            if p.isdir() and filter(p):
                for p2 in p.walk():
                    yield p2
    
    @property
    def basename(self):
        return os.path.basename(str(self))
    @property
    def dirname(self):
        return os.path.dirname(str(self))
    def up(self):
        return Path(self._location, self.dirname)
    
    def isdir(self):
        return self._location.isdir(str(self))
    def isfile(self):
        return self._location.isfile(str(self))
    def exists(self):
        return self._location.exists(str(self))
    def stat(self):
        return self._location.stat(str(self))
    
    def glob(self, pattern):
        return [Path(self._location, fn) 
            for fn in self._location.glob(str(self / pattern))]



# copy, move rename, delete, open

#def copy(self, dst, override = False):
#    dst = dst if isinstance(dst, Path) else Path(str(dst))
#    if override:
#        Path(dst).remove()
#    if self.isdir():
#        shutil.copytree(self.path, str(dst))
#    else:
#        shutil.copy2(self.path, str(dst))
#    return dst
#def move(self, dst):
#    shutil.move(self.path, str(dst))
#    return dst if isinstance(dst, Path) else Path(str(dst))
#def rename(self, newname):
#    """Renames the last element in the path. 
#    Example::
#    
#        >>> p = Path("/foo/bar/spam.txt")
#        >>> p2 = p.rename("bacon.txt")
#        >>> p2 == "/foo/bar/bacon.txt"
#        True
#    """
#    return self.move(Path(self.dirname, newname))
#def remove(self):
#    """removes the given path, if it exists; if this path is a directory, removes recursively"""
#    if not self.exists():
#        return
#    if self.isdir():
#        shutil.rmtree(self.path)
#    else:
#        os.remove(self.path)
#def mkdir(self):
#    """make a directory on this path (including all needed intermediate directories), if this
#    path doesn't already exist"""
#    if not self.exists():
#        os.makedirs(self.path)
#
#def open(self, fn, *args):
#    """opens a file at this path"""
#    return open(str(self / fn), *args)

#class Multimethod(object):
#    def __init__(self, name):
#        self.name = name
#        self._overloads = {}
#    def __repr__(self):
#        return "Multimethod(%r)" % (self.name,)
#    def overload(self, *args):
#        def overloader(func):
#            self._overloads[args] = func
#            return self
#        return overloader
#    def __call__(self, *args):
#        sig = tuple(type(a) for a in args)
#        if sig not in self._overloads:
#            raise TypeError("%r cannot apply to %s" % (self, sig))
#        return self._overloads[self](*args)
#
#
#def multimethod(*args):
#    def deco(func):
#        mm = Multimethod(func.__name__)
#        mm.overload(*args)(func)
#        return mm
#    return deco
#
#@multimethod(str, str)
#def copy(src, dst, override = True):
#    if override:
#        Path(dst).remove()
#    if src.isdir():
#        shutil.copytree(src, dst)
#    else:
#        shutil.copy2(src, dst)
#    return dst
#
#@copy.overload(Path, Path)
#def copy(src, dst):
#    copy(str(src), str(dst))
#    return dst
#
#@copy.overload(Path, str)
#def copy(src, dst):
#    copy(str(src), str(dst))
#    return Path(dst)
#
#@copy.overload(str, Path)
#def copy(src, dst):
#    copy(str(src), str(dst))
#    return Path(dst)

