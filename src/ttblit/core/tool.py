import importlib
import pkgutil

from .. import tool


class Tool():
    _by_command = {}

    def __init__(self, parser=None):
        self.parser = None
        if parser is not None:
            self.parser = parser.add_parser(self.command, help=self.help)

    def __init_subclass__(cls):
        if hasattr(cls, 'command'):
            cls._by_command[cls.command] = cls

    def run(self, args):
        raise NotImplementedError


# Load all the implementations dynamically.
for loader, module_name, is_pkg in pkgutil.walk_packages(tool.__path__, tool.__name__ + '.'):
    # We don't need to import anything from the modules. We just need to load them
    # so that the subclasses are created.
    importlib.import_module(module_name, tool.__name__)
