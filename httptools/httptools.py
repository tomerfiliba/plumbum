class HttpRequest(object):
    def __init__(self):
        pass

class HttpResponse(object):
    pass

class HttpException(Exception):
    def __init__(self, status, body, code = 500):
        pass

class HttpServer(object):
    def __init__(self, host, port, urlmap):
        pass

class Resource(object):
    pass

class XCLI(Resource):
    def default(self, req):
        pass
    def connect(self, req):
        pass
    def disconnect(self, req):
        pass
    def invoke(self, req):
        pass

