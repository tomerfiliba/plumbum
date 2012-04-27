from plumbum import local
from plumbum.local import grep

import logging
logging.basicConfig(level=logging.DEBUG)

ls = local["ls"]
x = (ls | grep["path"])
print x
print x()
