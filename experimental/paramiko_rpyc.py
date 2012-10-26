import rpyc
from plumbum.paramiko_machine import ParamikoMachine

mach = ParamikoMachine("192.168.1.143")
sock = mach.connect_sock(18812)
conn = rpyc.classic.connect_stream(rpyc.SocketStream(sock))
print conn.modules.sys
print conn.modules.sys.platform

#mach.close()
#conn.close()

