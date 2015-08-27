#!/usr/bin/env python
from __future__ import with_statement, print_function
from plumbum import colors

with colors:
    print("Do you believe in color, punk? DO YOU?")
    for i in range(0,255,10):
        for j in range(0,255,10):
            print(u''.join(colors.rgb(i,j,k)[u'\u2588'] for k in range(0,255,10)))

