from traits.trait_notifiers import set_ui_handler
import wx
from demo.view import DemoFrame

if __name__ == '__main__':
    set_ui_handler(wx.CallAfter)
    app = wx.App()
    DemoFrame(None).Show()
    app.MainLoop()
