import os
import gettext

# If not installed with setuptools, this might not be available
try:
    import pkg_resources
except ImportError:
    pkg_resources = None

try:
    from typing import Tuple, List, Callable
except ImportError:
    pass

local_dir = os.path.basename(__file__)

def get_translation_for(package_name): # type: (str) -> gettext.NullTranslations
    '''Find and return gettext translation for package
    (Try to find folder manually if setuptools does not exist)
    '''

    if '.' in package_name:
        package_name = '.'.join(package_name.split('.')[:-1])
    localedir = None

    if pkg_resources is None:
        mydir = os.path.join(local_dir, 'i18n')
    else:
        mydir = pkg_resources.resource_filename(package_name, 'i18n')

    for localedir in mydir, None:
        localefile = gettext.find(package_name, localedir)
        if localefile:
            break

    return gettext.translation(package_name, localedir=localedir, fallback=True)


def get_translation_functions(package_name, names=('gettext',)):
    # type: (str, Tuple[str, ...]) -> List[Callable[..., str]]
    'finds and installs translation functions for package'
    translation = get_translation_for(package_name)
    return [getattr(translation, x) for x in names]
