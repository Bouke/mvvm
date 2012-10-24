from __future__ import absolute_import

from traits.api import HasTraits, Instance, Any


class Wrapped(HasTraits):
    _wrapped = Instance(Any)

    def __init__(self, wrapped, auto_write=True, **kwargs):
        super(Wrapped, self).__init__()
        self._wrapped = wrapped

        for name in (n for n in dir(wrapped) if not n.startswith('_')):
            setattr(self, name, getattr(wrapped, name))

        if auto_write:
            self.on_trait_change(self._auto_write)
        else:
            self.changes = {}
            self.on_trait_change(self._add_change)

        self.trait_set(**kwargs)

    def _auto_write(self, name, value):
        setattr(self._wrapped, name, value)

    def _add_change(self, name, value):
        self.changes[name] = value

    def write(self):
        for name, value in self.changes.items():
            setattr(self._wrapped, name, value)

    def __eq__(self, other):
        if isinstance(other, self._wrapped.__class__):
            return self._wrapped == other
        if isinstance(other, self.__class__):
            return self._wrapped == other._wrapped

    def __ne__(self, other):
        return not self.__eq__(other)


def wrap(obj, auto_write=False):
    return wrap_cls(obj.__class__)(obj, auto_write)

cached = {}
def wrap_cls(cls):
    if not cls in cached:
        cached[cls] = type('Wrapped'+cls.__name__, (Wrapped,), {
            '_wrapped': Instance(cls),
        })
        for name in (n for n in dir(cls) if not n.startswith('_')):
            cached[cls].add_class_trait(name, Any)
    return cached[cls]
