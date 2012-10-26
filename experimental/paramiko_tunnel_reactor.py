import select
import socket
import threading


class SimpleReactor(object):
    __slots__ = ["_active", "_io_handlers"]
    
    def __init__(self):
        self._active = False
        self._io_handlers = []

    def add_handler(self, handler):
        self._io_handlers.append(handler)

    def _mainloop(self):
        while self._active:
            pruned = []
            for handler in self._io_handlers:
                try:
                    handler.fileno()
                except EnvironmentError:
                    pass
                else:
                    pruned.append(handler)
            self._io_handlers = pruned
            rlist, _, _ = select.select(self._io_handlers, (), (), 0.5)
            for handler in rlist:
                handler.handle()

    def start(self):
        if self._active:
            raise ValueError("reactor already running")
        self._active = True
        self._mainloop()
    def stop(self):
        self._active = False

reactor = SimpleReactor()
reactor_thread = threading.Thread(target = reactor.start)
reactor_thread.start()
#def shutdown_reactor_thread():
#    reactor.stop()
#    reactor_thread.join()
#atexit.register(shutdown_reactor_thread)

class ReactorHandler(object):
    __slots__ = ()
    def fileno(self):
        raise NotImplementedError()
    def close(self):
        pass

class Accepter(ReactorHandler):
    __slots__ = ["tunnel", "listener"]
    
    def __init__(self, tunnel, backlog = 5, family = socket.AF_INET, socktype = socket.SOCK_STREAM):
        self.tunnel = tunnel
        self.listener = socket.socket(family, socktype)
        self.listener.bind((tunnel.lhost, tunnel.lport))
        self.listener.listen(backlog)
    def close(self):
        self.listener.close()
    def fileno(self):
        return self.listener.fileno()
    def handle(self):
        sock, _ = self.listener.accept()
        chan = self.tunnel.transport.open_channel('direct-tcpip',
           (self.tunnel.dhost, self.tunnel.dport), sock.getpeername())
        if chan is None:
            raise ValueError("Rejected by server")
        self.tunnel.add_pair(chan, sock)

class Forwarder(ReactorHandler):
    __slots__ = ["srcsock", "dstsock"]
    CHUNK_SIZE = 1024
    
    def __init__(self, srcsock, dstsock):
        self.srcsock = srcsock
        self.dstsock = dstsock
    def fileno(self):
        return self.srcsock.fileno()
    def close(self):
        self.srcsock.shutdown(socket.SHUT_RDWR)
        self.srcsock.close()
        self.dstsock.shutdown(socket.SHUT_RDWR)
        self.dstsock.close()
    def handle(self):
        data = self.srcsock.recv(self.CHUNK_SIZE)
        if not data:
            self.shutdown()
        while data:
            count = self.dstsock.send(data)
            data = data[count:]

class ParamikoTunnel(object):
    def __init__(self, reactor, transport, lhost, lport, dhost, dport):
        self.reactor = reactor
        self.transport = transport
        self.lhost = lhost
        self.lport = lport
        self.dhost = dhost
        self.dport = dport
        self.accepter = Accepter(self)
        self.forwarders = []
        self.reactor.add_handler(self.accepter)

    def __repr__(self):
        return "<ParamikoTunnel %s:%s->%s:%s" % (self.lhost, self.lport, self.dhost, self.dport)

    def is_active(self):
        return bool(self.accepter)

    def close(self):
        if not self.accepter:
            return
        for fwd in self.forwarders:
            fwd.close()
        del self.forwarders[:]
        self.accepter.close()
        self.accepter = None

    def add_pair(self, chan, sock):
        f1 = Forwarder(chan, sock)
        f2 = Forwarder(sock, chan)
        self.forwarders.append(f1)
        self.forwarders.append(f2)
        self.reactor.add_handler(f1)
        self.reactor.add_handler(f2)
