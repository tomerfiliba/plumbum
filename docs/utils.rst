.. _guide-utils:

Utilities
=========

The ``utils`` module contains a collection of useful utility functions. Note that they are not
imported into the namespace of ``plumbum`` directly, and you have to explicitly import them, e.g.
``from plumbum.path.utils import copy``.

* :func:`copy(src, dst) <plumbum.path.utils.copy>` - Copies ``src`` to ``dst`` (recursively, if ``src``
  is a directory). The arguments can be either local or remote paths -- the function will sort
  out all the necessary details.
  
  * If both paths are local, the files are copied locally
  
  * If one path is local and the other is remote, the function uploads/downloads the files
  
  * If both paths refer to the same remote machine, the function copies the files locally on the
    remote machine
    
  * If both paths refer to different remote machines, the function downloads the files to a 
    temporary location and then uploads them to the destination
  
* :func:`move(src, dst) <plumbum.path.utils.move>` - Moves ``src`` onto ``dst``. The arguments can be 
  either local or remote -- the function will sort our all the necessary details (as in ``copy``)

* :func:`delete(*paths) <plumbum.path.utils.delete>` - Deletes the given sequence of paths; each path
  may be a string, a local/remote path object, or an iterable of paths. If any of the paths does
  not exist, the function silently ignores the error and continues. For example ::
  
    from plumbum.path.utils import delete
    delete(local.cwd // "*/*.pyc", local.cwd // "*/__pycache__")

