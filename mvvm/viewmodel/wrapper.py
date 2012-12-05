from weakref import ref
from sqlalchemy import event
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.attributes import InstrumentedAttribute
from traits.api import HasTraits, Instance
from traits.traits import Property


class Wrapped(HasTraits):
    def __init__(self, wrapped, **kwargs):
        super(Wrapped, self).__init__()
        self._wrapped = wrapped

        if not hasattr(wrapped, '_wrappers'):
            wrapped._wrappers = []
        wrapped._wrappers.append(ref(self))

        self.trait_set(**kwargs)

    def __eq__(self, other):
        if isinstance(other, self._wrapped.__class__):
            return self._wrapped == other
        if isinstance(other, self.__class__):
            return self._wrapped == other._wrapped

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        cls_self = self.__class__
        cls_wrapped = self._wrapped.__class__
        return '<%s.%s object at %s, wrapping %s.%s object at %s>' % (
            cls_self.__module__, cls_self.__name__, hex(id(self)),
            cls_wrapped.__module__, cls_wrapped.__name__, hex(id(self._wrapped)),
        )


class CachingWrapped(Wrapped):
    def __init__(self, wrapped, **kwargs):
        self.changes = kwargs
        super(CachingWrapped, self).__init__(wrapped, **kwargs)

    def flush(self):
        for name, value in self.changes.items():
            setattr(self._wrapped, name, unwrap(value))

    @property
    def has_changes(self):
        return bool(self.changes)


cached_classes = {
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
            setattr(self._wrapped, name, unwrap(value))
    else:
        def _set(self, value):
            self.changes[name] = value
            self.trait_property_changed(name, value)
    return _set

# @todo document this method
def sa_listener(name):
    def _listener(target, value, oldvalue, initiator):
        if not hasattr(target, '_wrappers'):
            return
        for wrapper in target._wrappers:
            wrapper = wrapper()
            if not wrapper:
                continue # weakref
            elif isinstance(wrapper, CachingWrapped):
                if name in wrapper.changes and wrapper.changes[name] == value:
                    del wrapper.changes[name]
                else:
                    setattr(wrapper, name, value)
            else:
                if getattr(target, name) != value:
                    wrapper.trait_property_changed(name, oldvalue, value)
    return _listener

# @todo document this method
def setup_sa_listeners(cls):
    if cls in cached_classes[True] or cls in cached_classes[False]:
        return
    try:
        class_mapper(cls) # fails if not an sqlalchemy class

        for name in [n for n in dir(cls) if not n.startswith('_')]:
            column = getattr(cls, name)
            if isinstance(column, InstrumentedAttribute):
                event.listen(column, 'set', sa_listener(name))
    except: pass

def wrap_cls(cls, transparent=True):
    """
    Wraps a class as either Wrapped or CachingWrapped.
    :rtype: type
    """
    if not cls in cached_classes[transparent]:
        setup_sa_listeners(cls)

        cls_name = '%sWrapped%s' % ('Transparent' if transparent else 'Caching',
                                    cls.__name__)
        cls_bases = (Wrapped if transparent else CachingWrapped,)
        cls_dict = {
            '_wrapped': Instance(cls),
        }
        for name in [n for n in dir(cls) if not n.startswith('_')]:
            cls_dict[name] = Property(getter(name, transparent),
                                      setter(name, transparent))
        cached_classes[transparent][cls] = type(cls_name, cls_bases, cls_dict)
    return cached_classes[transparent][cls]

def wrap(obj, transparent=True):
    """
    Wraps an object as either Wrapped or CachingWrapped.

    :rtype: Wrapped
    """
    if obj is None:
        raise TypeError('Cannot wrap None')
    return wrap_cls(obj.__class__, transparent)(obj)

def unwrap(obj):
    while isinstance(obj, Wrapped):
        obj = obj._wrapped
    return obj
