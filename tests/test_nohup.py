# -*- coding: utf-8 -*-
import os
import time

import psutil
import pytest

from plumbum import NOHUP, local

try:
    from plumbum.cmd import bash, echo
except ImportError:
    bash = None
    echo = None
from plumbum._testtools import skip_on_windows
from plumbum.path.utils import delete


@skip_on_windows
class TestNohupLocal:
    def read_file(self, filename):
        assert filename in os.listdir(".")
        with open(filename) as f:
            return f.read()

    @pytest.mark.usefixtures("testdir")
    def test_slow(self):
        delete("nohup.out")
        sp = bash["slow_process.bash"]
        sp & NOHUP
        time.sleep(0.5)
        assert self.read_file("slow_process.out") == "Starting test\n1\n"
        assert self.read_file("nohup.out") == "1\n"
        time.sleep(1)
        assert self.read_file("slow_process.out") == "Starting test\n1\n2\n"
        assert self.read_file("nohup.out") == "1\n2\n"
        time.sleep(2)
        delete("nohup.out", "slow_process.out")

    def test_append(self):
        delete("nohup.out")
        output = echo["This is output"]
        output & NOHUP
        time.sleep(0.2)
        assert self.read_file("nohup.out") == "This is output\n"
        output & NOHUP
        time.sleep(0.2)
        assert self.read_file("nohup.out") == "This is output\n" * 2
        delete("nohup.out")

    def test_redir(self):
        delete("nohup_new.out")
        output = echo["This is output"]

        output & NOHUP(stdout="nohup_new.out")
        time.sleep(0.2)
        assert self.read_file("nohup_new.out") == "This is output\n"
        delete("nohup_new.out")

        (output > "nohup_new.out") & NOHUP
        time.sleep(0.2)
        assert self.read_file("nohup_new.out") == "This is output\n"
        delete("nohup_new.out")

        output & NOHUP
        time.sleep(0.2)
        assert self.read_file("nohup.out") == "This is output\n"
        delete("nohup.out")

    def test_closed_filehandles(self):
        proc = psutil.Process()
        file_handles_prior = proc.num_fds()
        sleep_proc = local["sleep"]["1"] & NOHUP
        sleep_proc.wait()
        file_handles_after = proc.num_fds()
        assert file_handles_prior >= file_handles_after
