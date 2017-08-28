import gettext
import pkg_resources
try:
    from typing import Tuple, List, Callable
except ImportError:
    pass

def get_translation_for(package_name): # type: (str) -> gettext.NullTranslations
    'find and return gettext translation for package'
    if '.' in package_name:
        package_name = '.'.join(package_name.split('.')[:-1])
    localedir = None
    for localedir in pkg_resources.resource_filename(package_name, 'i18n'), None:
        localefile = gettext.find(package_name, localedir)
        if localefile:
            break
    else:
        pass
    return gettext.translation(package_name, localedir=localedir, fallback=True)


def get_translation_functions(package_name, names=('gettext',)):
    # type: (str, Tuple[str, ...]) -> List[Callable[..., str]]
    'finds and installs translation functions for package'
    translation = get_translation_for(package_name)
    return [getattr(translation, x) for x in names]
