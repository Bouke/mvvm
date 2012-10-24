from traits.api import HasTraits, Event


class CloseMixin(HasTraits):
    """Mixin providing a close event.

    `closed` is fired when the linked view should be closed. It can be set to
        the command firing the event, which can in turn be used to set the
        desired modal return value.
    """
    close = Event
