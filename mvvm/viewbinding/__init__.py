import wx
import wx.grid
from misc.controls import DateTimeCtrl

from mvvm.viewbinding.command import CommandBinding
from mvvm.viewbinding.display import ListBinding, LabelBinding, \
    StatusBarBinding
from mvvm.viewbinding.grid import GridBinding
from mvvm.viewbinding.interactive import CheckBinding, ChoiceBinding, TextBinding, \
    DateBinding, DateTimeBinding, ComboBinding, FileBinding, SliderBinding

def bind(field, *args, **kwargs):
    # command
    if isinstance(field, wx.Button) or isinstance(field, wx.MenuItem):
        return CommandBinding(field, *args, **kwargs)

    #display
    elif isinstance(field, wx.ListCtrl):
        return ListBinding(field, *args, **kwargs)
    elif isinstance(field, wx.StaticText):
        return LabelBinding(field, *args, **kwargs)

    #interactive
    elif isinstance(field, wx.TextCtrl):
        return TextBinding(field, *args, **kwargs)
    elif isinstance(field, wx.Slider):
        return SliderBinding(field, *args, **kwargs)
    elif isinstance(field, wx.DatePickerCtrlBase):
        return DateBinding(field, *args, **kwargs)

    else:
        raise NotImplementedError('Cannot bind instances of %s' % field.__class__)
