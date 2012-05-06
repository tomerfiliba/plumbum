Command-Line Interface (CLI)
============================

The other side of the coin of *executing programs* with ease is *writing CLI applications* 
with ease. Python scripts normally work with ``optparse`` and the more recent ``argparse``, 
but they both offer a quite-limited and a very unintuitive/unpythonic way to work with 
command-line arguments.

``plumbum.cli`` offers a different solution: instead of building parser objects and adding
switches to them imperatively, you write a class, where methods or attributes correspond 
to switches, and the ``main`` method is the entry-point of the program. A simple program
might look like so ::

    from plumbum import cli
    
    class MyApp(cli.Application):
        verbose = cli.Flag(["v, "verbose"], help = "If given, I will be very talkative")
        
        def main(self):
            print "This is my application"
            if self.verbose:
                print "Yadda " * 200
    
    if __name__ == "__main__":
        MyApp.run()

And here's a more interesting example

Application
-----------
* PROGNAME, VERSION, DESCRIPTION, USAGE
* docstring
* run, main, help, version

Interdependencies
-----------------
* Mandatory
* Requires
* Excludes

Switch Groups
-------------

Positional Arguments
--------------------


Attributes
----------
* SwitchAttr
* ToggleAttr
* Flag
* CountAttr

Argument Types
--------------
* Range
* Set









