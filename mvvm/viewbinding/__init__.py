import wx

from mvvm.viewbinding.display import LabelBinding
from mvvm.viewbinding.interactive import TextBinding


def bind(field, *args, **kwargs):
    if isinstance(field, wx.StaticText):
        return LabelBinding(field, *args, **kwargs)
    elif isinstance(field, wx.TextCtrl):
        return TextBinding(field, *args, **kwargs)
    else:
        raise NotImplementedError('Cannot bind instances of %s' % field.__class__)
