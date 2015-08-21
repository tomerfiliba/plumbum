#!/usr/bin/env python
"""
Examples::

    $ python geet.py
    no command given

    $ python geet.py leet
    unknown command 'leet'

    $ python geet.py --help
    geet v1.7.2
    The l33t version control

    Usage: geet.py [SWITCHES] [SUBCOMMAND [SWITCHES]] args...
    Meta-switches:
        -h, --help                 Prints this help message and quits
        -v, --version              Prints the program's version and quits

    Subcommands:
        commit                     creates a new commit in the current branch; see
                                   'geet commit --help' for more info
        push                       pushes the current local branch to the remote
                                   one; see 'geet push --help' for more info

    $ python geet.py commit --help
    geet commit v1.7.2
    creates a new commit in the current branch

    Usage: geet commit [SWITCHES]
    Meta-switches:
        -h, --help                 Prints this help message and quits
        -v, --version              Prints the program's version and quits

    Switches:
        -a                         automatically add changed files
        -m VALUE:str               sets the commit message; required

    $ python geet.py commit -m "foo"
    committing...
"""
from plumbum import cli

# To force no color support:
# from plumbum import colors
# colors.use_color = False

try:
    import colorama
    colorama.init()
    from plumbum import colors
    colors.use_color = True
except ImportError:
    pass

class Geet(cli.ColorfulApplication):
    """The l33t version control"""
    PROGNAME = "geet"
    VERSION = "1.7.2"
    COLOR_PROGNAME = None

    verbosity = cli.SwitchAttr("--verbosity", cli.Set("low", "high", "some-very-long-name", "to-test-wrap-around"),
        help = "sets the verbosity level of the geet tool. doesn't really do anything except for testing line-wrapping "
        "in help " * 3)

@Geet.subcommand("commit")
class GeetCommit(cli.ColorfulApplication):
    """creates a new commit in the current branch"""

    auto_add = cli.Flag("-a", help = "automatically add changed files")
    message = cli.SwitchAttr("-m", str, mandatory = True, help = "sets the commit message")

    def main(self):
        print("committing...")

GeetCommit.unbind_switches("-v", "--version")

@Geet.subcommand("push")
class GeetPush(cli.ColorfulApplication):
    """pushes the current local branch to the remote one"""

    tags = cli.Flag("--tags", help = "whether to push tags (default is False)")

    def main(self, remote, branch = "master"):
        print("pushing to %s/%s..." % (remote, branch))


if __name__ == "__main__":
    Geet.run()
