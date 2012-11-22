import wx
import wx.grid

from mvvm.viewbinding.command import CommandBinding
from mvvm.viewbinding.display import ListBinding, LabelBinding, \
    StatusBarBinding
from mvvm.viewbinding.grid import GridBinding
from mvvm.viewbinding.interactive import CheckBinding, ChoiceBinding, TextBinding, \
    DateBinding, DateTimeBinding, ComboBinding, FileBinding, SliderBinding
from misc.custom_control import DateTimeCtrl

def bind(field, *args, **kwargs):
    # command
    if isinstance(field, wx.Button) or isinstance(field, wx.MenuItem):
        return CommandBinding(field, *args, **kwargs)

    #display
    elif isinstance(field, wx.ListCtrl):
        return ListBinding(field, *args, **kwargs)
    elif isinstance(field, wx.StaticText):
        return LabelBinding(field, *args, **kwargs)
    elif isinstance(field, wx.StatusBar):
        return StatusBarBinding(field, *args, **kwargs)

    #interactive
    elif isinstance(field, DateTimeCtrl):#DateTimeCtrl inherit from TextCtrl so
                                         # it needs to be called first
        return DateTimeBinding(field, *args, **kwargs)
    elif isinstance(field, wx.TextCtrl):
        return TextBinding(field, *args, **kwargs)
    elif isinstance(field, wx.Slider):
        return SliderBinding(field, *args, **kwargs)
    elif isinstance(field, wx.RadioBox):
        return ChoiceBinding(field, *args, **kwargs)
    elif isinstance(field, wx.Choice):
        return ChoiceBinding(field, *args, **kwargs)
    elif isinstance(field, wx.ComboBox):
        return ComboBinding(field, *args, **kwargs)
    elif isinstance(field, wx.CheckBox):
        return CheckBinding(field, *args, **kwargs)
    elif isinstance(field, wx.DatePickerCtrlBase):
        return DateBinding(field, *args, **kwargs)
    elif isinstance(field, wx.FilePickerCtrl):
        return FileBinding(field, *args, **kwargs)

    #grid2
    elif isinstance(field, wx.grid.Grid):
        return GridBinding(field, *args, **kwargs)

    else:
        raise NotImplementedError('Cannot bind instances of %s' % field.__class__)
