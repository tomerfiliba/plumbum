"""
Progress bar
------------
"""
from __future__ import print_function, division
import warnings
from abc import abstractmethod
import datetime
from plumbum.lib import six
from plumbum.cli.termsize import get_terminal_size
import sys

class ProgressBase(six.ABC):
    """Base class for progress bars. Customize for types of progress bars.

    :param iterator: The iterator to wrap with a progress bar
    :param length: The length of the iterator (will use ``__len__`` if None)
    :param timer: Try to time the completion status of the iterator
    :param body: True if the slow portion occurs outside the iterator (in a loop, for example)
    :param has_output: True if the iteration body produces output to the screen (forces rewrite off)
    :param clear: Clear the progress bar afterwards, if applicable.
    """

    def __init__(self, iterator=None, length=None, timer=True, body=False, has_output=False, clear=True):
        if length is None:
            length = len(iterator)
        elif iterator is None:
            iterator = range(length)
        elif length is None and iterator is None:
            raise TypeError("Expected either an iterator or a length")

        self.length = length
        self.iterator = iterator
        self.timer = timer
        self.body = body
        self.has_output = has_output
        self.clear = clear

    def __len__(self):
        return self.length

    def __iter__(self):
        self.start()
        return self

    @abstractmethod
    def start(self):
        """This should initialize the progress bar and the iterator"""
        self.iter = iter(self.iterator)
        self.value = -1 if self.body else 0
        self._start_time = datetime.datetime.now()

    def __next__(self):
        try:
            rval = next(self.iter)
            self.increment()
        except StopIteration:
            self.done()
            raise
        return rval

    def next(self):
        return self.__next__()

    @property
    def value(self):
        """This is the current value, as a property so setting it can be customized"""
        return self._value
    @value.setter
    def value(self, val):
        self._value = val

    @abstractmethod
    def display(self):
        """Called to update the progress bar"""
        pass

    def increment(self):
        """Sets next value and displays the bar"""
        self.value += 1
        self.display()

    def time_remaining(self):
        """Get the time remaining for the progress bar, guesses"""
        if self.value < 1:
            return None, None
        elapsed_time = datetime.datetime.now() - self._start_time
        time_each = (elapsed_time.days*24*60*60
                     + elapsed_time.seconds
                     + elapsed_time.microseconds/1000000.0) / self.value
        time_remaining = time_each * (self.length - self.value)
        return elapsed_time, datetime.timedelta(0,time_remaining,0)

    def str_time_remaining(self):
        """Returns a string version of time remaining"""
        if self.value < 1:
            return "Starting...                         "
        else:
            elapsed_time, time_remaining = list(map(str,self.time_remaining()))
            return "{0} completed, {1} remaining".format(elapsed_time.split('.')[0],
                                                       time_remaining.split('.')[0])

    @abstractmethod
    def done(self):
        """Is called when the iterator is done."""
        pass

    @classmethod
    def range(cls, *value, **kargs):
        """Fast shortcut to create a range based progress bar, assumes work done in body"""
        return cls(range(*value), body=True, **kargs)

    @classmethod
    def wrap(cls, iterator, length=None, **kargs):
        """Shortcut to wrap an iterator that does not do all the work internally"""
        return cls(iterator, length, body = True, **kargs)


class Progress(ProgressBase):

    def start(self):
        super(Progress, self).start()
        self.display()

    def done(self):
        self.value = self.length
        self.display()
        if self.clear and not self.has_output:
            print("\r", len(str(self)) * " ", "\r", end='', sep='')
        else:
            print()


    def __str__(self):
        percent = max(self.value,0)/self.length
        width = get_terminal_size(default=(0,0))[0]
        ending = ' ' + (self.str_time_remaining()
            if self.timer else '{0} of {1} complete'.format(self.value, self.length))
        if width - len(ending) < 10 or self.has_output:
            self.width = 0
            if self.timer:
                return "{0:.0%} complete: {1}".format(percent, self.str_time_remaining())
            else:
                return "{0:.0%} complete".format(percent)

        else:
            self.width = width - len(ending) - 2 - 1
            nstars = int(percent*self.width)
            pbar = '[' + '*'*nstars + ' '*(self.width-nstars) + ']' + ending

        str_percent = ' {0:.0%} '.format(percent)

        return pbar[:self.width//2 - 2] + str_percent + pbar[self.width//2+len(str_percent) - 2:]


    def display(self):
        disptxt = str(self)
        if self.width == 0 or self.has_output:
            print(disptxt)
        else:
            print("\r", end='')
            print(disptxt, end='')
            sys.stdout.flush()


class ProgressIPy(ProgressBase): # pragma: no cover
    HTMLBOX = '<div class="widget-hbox widget-progress"><div class="widget-label" style="display:block;">{}</div></div>'

    def __init__(self, *args, **kargs):

        # Ipython gives warnings when using widgets about the API potentially changing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                from ipywidgets import IntProgress, HTML, HBox # type: ignore
            except ImportError: # Support IPython < 4.0
                from IPython.html.widgets import IntProgress, HTML, HBox # type: ignore

        super(ProgressIPy, self).__init__(*args, **kargs)
        self.prog = IntProgress(max=self.length)
        self._label = HTML()
        self._box = HBox((self.prog, self._label))

    def start(self):
        from IPython.display import display # type: ignore
        display(self._box)
        super(ProgressIPy, self).start()

    @property
    def value(self):
        """This is the current value, -1 allowed (automatically fixed for display)"""
        return self._value
    @value.setter
    def value(self, val):
        self._value = val
        self.prog.value = max(val, 0)
        self.prog.description = "{0:.2%}".format(self.value / self.length)
        if self.timer and val > 0:
            self._label.value = self.HTMLBOX.format(self.str_time_remaining())

    def display(self):
        pass

    def done(self):
        if self.clear:
            self._box.close()


class ProgressAuto(ProgressBase):
    """Automatically selects the best progress bar (IPython HTML or text). Does not work with qtconsole
    (as that is correctly identified as identical to notebook, since the kernel is the same); it will still
    iterate, but no graphical indication will be diplayed.

    :param iterator: The iterator to wrap with a progress bar
    :param length: The length of the iterator (will use ``__len__`` if None)
    :param timer: Try to time the completion status of the iterator
    :param body: True if the slow portion occurs outside the iterator (in a loop, for example)
    """
    def __new__(cls, *args, **kargs):
        """Uses the generator trick that if a cls instance is returned, the __init__ method is not called."""
        try: # pragma: no cover
            __IPYTHON__
            try:
                from traitlets import TraitError # type: ignore
            except ImportError: # Support for IPython < 4.0
                from IPython.utils.traitlets import TraitError # type: ignore

            try:
                return ProgressIPy(*args, **kargs)
            except TraitError:
                raise NameError()
        except (NameError, ImportError):
            return Progress(*args, **kargs)

ProgressAuto.register(ProgressIPy)
ProgressAuto.register(Progress)

def main():
    import time
    tst = Progress.range(20)
    for i in tst:
        time.sleep(1)

if __name__ == '__main__':
    main()
