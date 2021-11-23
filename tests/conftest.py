# -*- coding: utf-8 -*-
import os
import sys
import tempfile

import pytest

if sys.version_info[0] < 3:
    collect_ignore = ["test_3_cli.py"]

SDIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def testdir():
    os.chdir(SDIR)


@pytest.fixture()
def cleandir():
    newpath = tempfile.mkdtemp()
    os.chdir(newpath)


# Pulled from https://github.com/reece/pytest-optional-tests

"""implements declaration of optional tests using pytest markers

The MIT License (MIT)

Copyright (c) 2019 Reece Hart

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""


import itertools
import logging
import re

import pytest

_logger = logging.getLogger(__name__)

marker_re = re.compile(r"^(?P<marker>\w+)(:\s*(?P<description>.*))?")


def pytest_addoption(parser):
    group = parser.getgroup("collect")
    group.addoption(
        "--run-optional-tests",
        action="append",
        dest="run_optional_tests",
        default=None,
        help="Optional test markers to run, multiple and/or comma separated okay",
    )
    parser.addini(
        "optional_tests", "list of optional markers", type="linelist", default=""
    )


def pytest_configure(config):
    # register all optional tests declared in ini file as markers
    # https://docs.pytest.org/en/latest/writing_plugins.html#registering-custom-markers
    ot_ini = config.inicfg.get("optional_tests").splitlines()
    for ot in ot_ini:
        # ot should be a line like "optmarker: this is an opt marker", as with markers section
        config.addinivalue_line("markers", ot)
    ot_markers = {marker_re.match(l).group(1) for l in ot_ini}

    # collect requested optional tests
    ot_run = config.getoption("run_optional_tests")
    if ot_run:
        ot_run = list(itertools.chain.from_iterable(a.split(",") for a in ot_run))
    else:
        ot_run = config.inicfg.get("run_optional_tests", [])
        if ot_run:
            ot_run = list(re.split(r"[,\s]+", ot_run))
    ot_run = set(ot_run)

    _logger.info("optional tests to run:", ot_run)
    if ot_run:
        unknown_tests = ot_run - ot_markers
        if unknown_tests:
            raise ValueError(
                "Requested execution of undeclared optional tests: {}".format(
                    ", ".join(unknown_tests)
                )
            )

    config._ot_markers = set(ot_markers)
    config._ot_run = set(ot_run)


def pytest_collection_modifyitems(config, items):
    # https://stackoverflow.com/a/50114028/342839
    ot_markers = config._ot_markers
    ot_run = config._ot_run

    skips = {}
    for item in items:
        marker_names = {m.name for m in item.iter_markers()}
        if not marker_names:
            continue
        test_otms = marker_names & ot_markers
        if not test_otms:
            # test is not marked with any optional marker
            continue
        if test_otms & ot_run:
            # test is marked with an enabled optional test; don't skip
            continue
        mns = str(marker_names)
        if mns not in skips:
            skips[mns] = pytest.mark.skip(
                reason="Skipping; marked with disabled optional tests ({})".format(
                    ", ".join(marker_names)
                )
            )
        item.add_marker(skips[mns])
