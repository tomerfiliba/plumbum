# -*- coding: utf-8 -*-
from plumbum import local
from plumbum.paramiko_machine import ParamikoMachine as PM

local.env.path.append("c:\\progra~1\\git\\bin")
from plumbum.cmd import grep, ls  # noqa: E402

m = PM("192.168.1.143")
mls = m["ls"]
mgrep = m["grep"]
# (mls | mgrep["b"])()

(mls | grep["\\."])()

(ls | mgrep["\\."])()
