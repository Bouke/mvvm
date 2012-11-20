from traits.api import HasTraits, Instance
from traits.traits import Property


class Wrapped(HasTraits):
    def __init__(self, wrapped, **kwargs):
        super(Wrapped, self).__init__()
        self._wrapped = wrapped
        self.trait_set(**kwargs)

    def __eq__(self, other):
        if isinstance(other, self._wrapped.__class__):
            return self._wrapped == other
        if isinstance(other, self.__class__):
            return self._wrapped == other._wrapped

    def __ne__(self, other):
        return not self.__eq__(other)


class CachingWrapped(Wrapped):
    def __init__(self, wrapped, **kwargs):
        self.changes = kwargs
        super(CachingWrapped, self).__init__(wrapped, **kwargs)

    def flush(self):
        for name, value in self.changes.items():
            setattr(self._wrapped, name, value)

    @property
    def has_changes(self):
        return bool(self.changes)


cached = {
    True: {},
    False: {},
}

def getter(name, transparent):
    if transparent:
        def _get(self):
            return getattr(self._wrapped, name)
    else:
        def _get(self):
            if name in self.changes:
                return self.changes[name]
            return getattr(self._wrapped, name)
    return _get

def setter(name, transparent):
    if transparent:
        def _set(self, value):
            setattr(self._wrapped, name, value)
            self.trait_property_changed(name, value)
    else:
        def _set(self, value):
            self.changes[name] = value
            self.trait_property_changed(name, value)
    return _set

def wrap_cls(cls, transparent=True):
    """
    Wraps a class as either Wrapped or CachingWrapped.

    :rtype: type
    """
    if not cls in cached[transparent]:
        cls_name = '%sWrapped%s' % ('Transparent' if transparent else 'Caching',
                                    cls.__name__)
        cls_bases = (Wrapped if transparent else CachingWrapped,)
        cls_dict = {
            '_wrapped': Instance(cls),
        }
        for name in (n for n in dir(cls) if not n.startswith('_')):
            cls_dict[name] = Property(getter(name, transparent),
                                      setter(name, transparent))
        cached[transparent][cls] = type(cls_name, cls_bases, cls_dict)
    return cached[transparent][cls]

def wrap(obj, transparent=True):
    """
    Wraps an object as either Wrapped or CachingWrapped.

    :rtype: Wrapped
    """
    return wrap_cls(obj.__class__, transparent)(obj)

def unwrap(obj):
    while isinstance(obj, Wrapped):
        obj = obj._wrapped
    return obj
