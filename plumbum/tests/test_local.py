from plumbum import local
from plumbum.local import grep

ls = local["ls"]
x = (ls | grep["test"])
print x()

