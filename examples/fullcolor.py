#!/usr/bin/env python3
from __future__ import annotations

from plumbum import colors

with colors:
    print("Do you believe in color, punk? DO YOU?")
    for i in range(0, 255, 10):
        for j in range(0, 255, 10):
            print("".join(colors.rgb(i, j, k)["\u2588"] for k in range(0, 255, 10)))
