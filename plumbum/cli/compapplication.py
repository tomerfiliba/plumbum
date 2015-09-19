# -*- coding: utf-8 -*-
"""
Created on Sat Sep 19 15:30:43 2015

@author: henryiii
"""

from plumbum.cli import Application
from plumbum.cli.argcompleter import ArgCompleter

class CompApplication(Application):

    @classmethod
    def _autocomplete_args(cls, comp_line, comp_point, ifs=' '):
        """This is a comp_line seperated by ifs, with the cursor at comp_point"""

        words = comp_line.strip().split()[1:] # remove progname

        if not words:
            return ['']

        self = cls('argcompleter')
        names = ['-'+a for a in self._switches_by_name if len(a)==1]
        names += ['--'+a for a in self._switches_by_name if len(a)!=1]

        if words[-1][0] == '-':
            return [n for n in names if words[-1] in n]

        if comp_point < 0:
            return


    @classmethod
    def autocomplete(cls, argv=None):
        argcom = ArgCompleter()
        if not argcom.active:
            return
        comps = cls._autocomplete_args(*argcom.get_line())
        argcom.send_completions(comps)
        argcom.done()