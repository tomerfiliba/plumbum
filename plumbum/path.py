class FSUser(int):
    """A special object that represents file-system user. It derives from ``int``, so it behaves 
    just like a number (``uid``/``gid``), but also have a ``.name`` attribute that holds the
    string-name of the user, if given
    """
    def __new__(cls, val, name = None):
        self = int.__new__(cls, val)
        self.name = name
        return self

class Path(object):
    """An abstraction over file system paths. This class is abstract, and the two implementations
    are :class:`LocalPath <plumbum.local_machine.LocalPath>` and
    :class:`RemotePath <plumbum.remote_machine.RemotePath>`.
    """

    __slots__ = []
    CASE_SENSITIVE = True

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, str(self))
    def __div__(self, other):
        """Joins two paths"""
        return self.join(other)
    __truediv__ = __div__
    def __floordiv__(self, expr):
        """Returns a (possibly empty) list of paths that matched the glob-pattern under this path"""
        return self.glob(expr)
    def __iter__(self):
        """Iterate over the files in this directory"""
        return iter(self.list())
    def __eq__(self, other):
        if isinstance(other, Path):
            return self._get_info() == other._get_info()
        elif isinstance(other, str):
            if self.CASE_SENSITIVE:
                return str(self) == other
            else:
                return str(self).lower() == other.lower()
        else:
            return NotImplemented
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
        if self.CASE_SENSITIVE:
            return hash(str(self))
        else:
            return hash(str(self).lower())
    def __nonzero__(self):
        return bool(str(self))
    __bool__ = __nonzero__

    def up(self, count = 1):
        """Go up in ``count`` directories (the default is 1)"""
        return self.join("../" * count)
    def walk(self, filter = lambda p: True): #@ReservedAssignment
        """traverse all (recursive) sub-elements under this directory, that match the given filter.
        By default, the filter accepts everything; you can provide a custom filter function that
        takes a path as an argument and returns a boolean"""
        for p in self.list():
            if filter(p):
                yield p
                if p.isdir():
                    for p2 in p.walk():
                        yield p2

    @property
    def basename(self):
        """The basename component of this path"""
        raise NotImplementedError()
    @property
    def dirname(self):
        """The dirname component of this path"""
        raise NotImplementedError()
    @property
    def uid(self):
        """The user that owns this path. The returned value is a :class:`FSUser <plumbum.path.FSUser>`
        object which behaves like an ``int`` (as expected from ``uid``), but it also has a ``.name``
        attribute that holds the string-name of the user"""
        raise NotImplementedError()
    @property
    def gid(self):
        """The group that owns this path. The returned value is a :class:`FSUser <plumbum.path.FSUser>`
        object which behaves like an ``int`` (as expected from ``gid``), but it also has a ``.name``
        attribute that holds the string-name of the group"""
        raise NotImplementedError()

    def _get_info(self):
        raise NotImplementedError()
    def join(self, *parts):
        """Joins this path with any number of paths"""
        raise NotImplementedError()
    def list(self):
        """Returns the files in this directory"""
        raise NotImplementedError()
    def isdir(self):
        """Returns ``True`` if this path is a directory, ``False`` otherwise"""
        raise NotImplementedError()
    def isfile(self):
        """Returns ``True`` if this path is a regular file, ``False`` otherwise"""
        raise NotImplementedError()
    def exists(self):
        """Returns ``True`` if this path exists, ``False`` otherwise"""
        raise NotImplementedError()
    def stat(self):
        raise NotImplementedError()
    def glob(self, pattern):
        """Returns a (possibly empty) list of paths that matched the glob-pattern under this path"""
        raise NotImplementedError()
    def delete(self):
        """Deletes this path (recursively, if a directory)"""
        raise NotImplementedError()
    def move(self, dst):
        """Moves this path to a different location"""
        raise NotImplementedError()
    def rename(self, newname):
        """Renames this path to the ``new name`` (only the basename is changed)"""
        return self.move(self.up() / newname)
    def copy(self, dst, override = False):
        """Copies this path (recursively, if a directory) to the destination path"""
        raise NotImplementedError()
    def mkdir(self):
        """Creates a directory at this path; if the directory already exists, silently ignore"""
        raise NotImplementedError()
    def open(self, mode = "r"):
        """opens this path as a file"""
        raise NotImplementedError()
    def read(self):
        """returns the contents of this file"""
        raise NotImplementedError()
    def write(self, data):
        """writes the given data to this file"""
        raise NotImplementedError()
    def chown(self, owner=None, group=None, recursive=None):
        """Change ownership of this path.
        
        :param owner: The owner to set (either ``uid`` or ``username``), optional
        :param owner: The group to set (either ``gid`` or ``groupname``), optional
        :param recursive: whether to change ownership of all contained files and subdirectories.
                          Only meaningful when ``self`` is a directory. If ``None``, the value
                          will default to ``True`` if ``self`` is a directory, ``False`` otherwise.
        """
        raise NotImplementedError()

