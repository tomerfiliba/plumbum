def setdoc(super):
    def deco(func):
        func.__doc__ = getattr(getattr(super, func.__name__, None), "__doc__", None)
        return func
    return deco
