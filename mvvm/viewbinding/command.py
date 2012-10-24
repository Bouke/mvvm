import wx
from traits.api import HasTraits, Bool, Event


class Command(HasTraits):
    can_execute = Bool
    execute = Event

    def __init__(self, handler=None, can_execute=True):
        self.can_execute = can_execute

        if handler:
            self.on_trait_change(lambda: handler(), 'execute')


class CommandBinding(object):
    def __init__(self, field, instance, trait):
        command = getattr(instance, trait)

        command.on_trait_change(lambda: field.Enable(command.can_execute),
            'can_execute', dispatch='ui')
        field.Enable(command.can_execute)

        # Register execute callback
        handler = lambda e: setattr(command, 'execute', True) and e.Skip()
        if isinstance(field, wx.MenuItem):
            frame =  field.GetMenu().GetMenuBar().GetFrame()
            frame.Bind(wx.EVT_MENU, handler, id=field.GetId())
        else:
            field.Bind(wx.EVT_BUTTON, handler)
