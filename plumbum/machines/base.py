from plumbum.commands.processes import CommandNotFound


class BaseMachine(object):
    """This is a base class for other machines. It contains common code to
    all machines in Plumbum."""


    def get(self, cmd, *othercommands):
        """This works a little like the ``.get`` method with dict's, only
        it supports an unlimited number of arguments, since later arguments
        are tried as commands and could also fail. It
        will try to call the first command, and if that is not found,
        it will call the next, etc. Will raise if no file named for the
        executable if a path is given, unlike ``[]`` access.

        Usage::

            best_zip = local.get('pigz','gzip')
        """
        try:
            command = self[cmd]
            if not command.executable.exists():
                raise CommandNotFound(cmd,command.executable)
            else:
                return command
        except CommandNotFound:
            if othercommands:
                return self.get(othercommands[0],*othercommands[1:])
            else:
                raise

    def __contains__(self, cmd):
        """Tests for the existance of the command, e.g., ``"ls" in plumbum.local``.
        ``cmd`` can be anything acceptable by ``__getitem__``.
        """
        try:
            self[cmd]
        except CommandNotFound:
            return False
        else:
            return True


