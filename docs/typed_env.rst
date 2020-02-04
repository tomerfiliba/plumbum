.. _guide-typed-env:

TypedEnv
========
Plumbum provides this utility class to facilitate working with environment variables.
Similar to how :class:`plumbum.cli.Application` parses command line arguments into pythonic data types,
:class:`plumbum.typed_env.TypedEnv` parses environment variables:

class MyEnv(TypedEnv):
    username = TypedEnv.Str("USER", default='anonymous')
    path = TypedEnv.CSV("PATH", separator=":", type=local.path)
    tmp = TypedEnv.Str(["TMP", "TEMP"])  # support 'fallback' var-names
    is_travis = TypedEnv.Bool("TRAVIS", default=False)  # True is 'yes/true/1' (case-insensitive)

We can now instantiate this class to access its attributes::

    >>> env = MyEnv()
    >>> env.username
    'ofer'

    >>> env.path
    [<LocalPath /home/ofer/bin>,
     <LocalPath /usr/local/bin>,
     <LocalPath /usr/local/sbin>,
     <LocalPath /usr/sbin>,
     <LocalPath /usr/bin>,
     <LocalPath /sbin>,
     <LocalPath /bin>]

    >>> env.tmp
    Traceback (most recent call last):
      [...]
    KeyError: 'TMP'

    >>> env.is_travis
    False

Finally, our ``TypedEnv`` object allows us ad-hoc access to the rest of the environment variables, using dot-notation::

    >>> env.HOME
    '/home/ofer'

We can also update the environment via our ``TypedEnv`` object:

    >>> env.tmp = "/tmp"
    >>> env.tmp
    '/tmp'

    >>> from os import environ
    >>> env.TMP
    '/tmp'

    >>> env.is_travis = True
    >>> env.TRAVIS
    'yes'

    >>> env.path = [local.path("/a"), local.path("/b")]
    >>> env.PATH
    '/a:/b'


TypedEnv as an Abstraction Layer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``TypedEnv`` class is very useful for separating your application from the actual environment variables.
It provides a layer where parsing and normalizing can take place in a centralized fashion.

For example, you might start with this simple implementation::

    class CiBuildEnv(TypedEnv):
        job_id = TypedEnv.Str("BUILD_ID")


Later, as the application gets more complicated, you may expand your implementation like so::

    class CiBuildEnv(TypedEnv):
        is_travis = TypedEnv.Bool("TRAVIS", default=False)
        _travis_job_id = TypedEnv.Str("TRAVIS_JOB_ID")
        _jenkins_job_id = TypedEnv.Str("BUILD_ID")

        @property
        def job_id(self):
            return self._travis_job_id if self.is_travis else self._jenkins_job_id



TypedEnv vs. local.env
^^^^^^^^^^^^^^^^^^^^^^

It is important to note that ``TypedEnv`` is separate and unrelated to the ``LocalEnv`` object that is provided via ``local.env``.

While ``TypedEnv`` reads and writes directly to ``os.environ``,
``local.env`` is a frozen copy taken at the start of the python session.

While ``TypedEnv`` is focused on parsing environment variables to be used by the current process,
``local.env``'s primary purpose is to manipulate the environment for child processes that are spawned
via plumbum's :ref:`local commands <guide-local-commands>`.
