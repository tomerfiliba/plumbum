About
=====

The project has been inspired by `PBS <https://github.com/amoffat/pbs>`_ of Andrew Moffat,
and has borrowed some of his ideas (namely importing commands). However, I felt there was too
much magic going on in PBS, and that the syntax wasn't what I had in mind when I came to write
shell programs. I contacted Andrew, but he wanted to keep PBS this way.

Besides PBS, the main purpose of the library was to be able to control remote machines with ease,
without imposing any requirements other than SSH. It began with an idea of 
`Rotem Yaari <https://github.com/vmalloc/>`_ for a libary called ``pyplatform``, which was
neglected for some time now. Plumbum attempts to revive this, and throw in some extra features
too. Ultimately, it aims to replace ``subprocess.Popen`` altogether.
