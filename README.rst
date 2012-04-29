Plumbum: Shell Combinators
==========================

Ever wanted wrist-handiness of shell scripts, but in a modern, object-oriented language and 
a rich library? Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*) is a small 
yet very functional library for writing programs a la shell scripts, but in python, of course. 
Plumbum treats programs as functions, which you can invoke to get run the program, and form
pipelines, just like you'd do in shells.

See http://plumbum.readthedocs.org for more info.


About
-----
The project has been inspired by `PBS <https://github.com/amoffat/pbs>`_ of Andrew Moffat,
and has borrowed some of his ideas (namely importing commands). However, I felt there was too
much magic going on in PBS, and that the syntax wasn't what I had in mind when I came to write
shell programs. I contacted Andrew, but he wanted to keep PBS this way.

Besides PBS, the main purpose of the library was to be able to control remote machines with ease,
without imposing any requirements other than SSH. It began with an idea of 
`Rotem Yaari <https://github.com/vmalloc/>`_ for a libary called `pyplatform`, which was
neglected for some time now. Plumbum attempts to revive this, and throw in some extra features
too. Ultimately, it aims to replace `subprocess.Popen` altogether.

