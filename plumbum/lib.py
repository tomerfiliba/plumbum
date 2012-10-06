import heapq


def _setdoc(super): #@ReservedAssignment
    def deco(func):
        func.__doc__ = getattr(getattr(super, func.__name__, None), "__doc__", None)
        return func
    return deco

class MinHeap(object):
    def __init__(self, items = ()):
        self._items = list(items)
        heapq.heapify(self._items)
    def __len__(self):
        return len(self._items)
    def push(self, item):
        heapq.heappush(self._items, item)
    def pop(self):
        heapq.heappop(self._items)
    def peek(self):
        return self._items[0]

