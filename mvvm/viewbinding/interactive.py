from __future__ import absolute_import
from collections import OrderedDict
import datetime, time, re

import wx


class CheckBinding(object):
    def __init__(self, field, trait, readonly=False, values=(False, True)):
        self.field, self.trait, self.values = (field, trait, values)
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view(getattr(*trait))

        if not readonly:
            field.Bind(wx.EVT_CHECKBOX, self.update_model)

    def update_view(self, new):
        self.field.SetValue(new == self.values[1])

    def update_model(self, event):
        value = self.values[self.field.GetValue()]
        if getattr(*self.trait) != value:
            setattr(self.trait[0], self.trait[1], value)
        event.Skip()


class ChoiceBinding(object):
    def __init__(self, field, trait, choices, readonly=False):
        if hasattr(choices, 'get_choices'):
            choices = OrderedDict(choices.get_choices())
        self.field, self.trait, self.readonly = (
            field, trait, readonly)

        # choices can be a tuple (instance, trait)
        if isinstance(choices, (list, tuple)) and len(choices) == 2:
            def update_choices():
                self.choices = getattr(choices[0], choices[1])
                self.update_choices()
            update_choices()
            choices[0].on_trait_change(update_choices, choices[1], dispatch='ui')
        else:
            self.choices = choices
            self.update_choices()

        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view(new=getattr(*trait))
        self.update_model(None)

        if not readonly:
            field.Bind(wx.EVT_CHOICE, self.update_model)

    def update_choices(self):
        field = self.field
        if isinstance(field, wx.RadioBox):
            self.field = wx.RadioBox(field.Parent, field.GetId(), field.GetLabel(),
                wx.DefaultPosition, wx.DefaultSize, self.choices.values(), 1,
                field.GetWindowStyleFlag())
            field.Parent.GetSizer().Replace(field, self.field)
            field.Destroy()
            if not self.readonly:
                self.field.Bind(wx.EVT_RADIOBOX, self.update_model)
        else:
            field.SetItems(self.choices.values())
        self.update_view(new=getattr(*self.trait))

        # resize frame if Minimalistic
        if hasattr(self.field.TopLevelParent, 'update_minimal_size'):
            # First, invalidate all parents
            parent = self.field.Parent
            while parent:
                parent.InvalidateBestSize()
                parent = parent.Parent
            self.field.TopLevelParent.update_minimal_size()

    def update_view(self, new):
        if len(self.choices) == 0: return
        try:
            self.field.SetSelection(self.choices.keys().index(new))
        except ValueError: pass

    def update_model(self, event):
        if 0 <= self.field.GetSelection() < len(self.choices.keys()):
            value = self.choices.keys() [self.field.GetSelection()]
            if getattr(*self.trait) != value:
                setattr(self.trait[0], self.trait[1], value)
        if event: event.Skip()


class ComboBinding(object):
    def __init__(self, field, trait, choice_provider):
        self.field, self.trait, self.choice_provider = (field, trait, choice_provider)

        field.Bind(wx.EVT_TEXT, self._on_text)
        field.Bind(wx.EVT_CHAR, self._on_char)
        field.Bind(wx.EVT_COMBOBOX, self._on_combobox)
        self._update_view(getattr(*trait))

    def _update_view(self, data):
        text = self.choice_provider.get_display_text(data)
        self.field.SetValue(text)
        self.field.SetStringSelection(text)

    def _on_text(self, event):
        # Once a selection has been made, do not modify the items of this
        # control. EVT_TEXT is also fired on Windows when making a
        # selection, which would change items listed and finally resulting
        # in an invalid selection as the selected item will become the first
        # item (0).
        if self.field.GetSelection() != -1:
            return

        # Remove the current selected option when no text entered
        if not self.field.GetValue():
            setattr(self.trait[0], self.trait[1], None)

        self.field.Freeze()

        # On Windows, clearing the control also removes the typed text. So
        # instead of clearing, delete all items.
        while not self.field.IsEmpty():
            self.field.Delete(0)

        choices = self.choice_provider.get_choices(self.field.GetValue())
        for data, text in choices:
            self.field.Append(text, data)

        if wx.Platform == '__WXMAC__':
            if len(choices): self.field.Popup()

        self.field.Thaw()
        event.Skip()

    def _on_combobox(self, event):
        if event.Selection != -1:
            self._update_model(event.Selection)
        event.Skip()

    def _update_model(self, idx):
        value = self.field.GetClientData(idx)
        if getattr(*self.trait) != value:
            setattr(self.trait[0], self.trait[1], value)

    def _on_char(self, evt):
        """
        Provides auto completion.

        As characters are received, the keys are written to the field. This
        triggers `_on_text`, which updates the list of choices. Then this
        method checks if there is an item starting with the typed text. If so,
        this item is selected and the remaining text next to the cursor text
        selected.
        """
        if evt.UnicodeKey not in (wx.WXK_NONE, wx.WXK_BACK, wx.WXK_ESCAPE):
            self.field.WriteText(unichr(evt.UnicodeKey))
            # re.I for case-insensitive text matching
            text = re.compile(self.field.GetValue(), re.I)
            for item_idx, item in enumerate(self.field.Items):
                if not text.match(item):
                    continue
                pos = self.field.InsertionPoint
                self.field.SetSelection(item_idx)
                self._update_model(item_idx)

                # Restore cursor position and set selection to appended part
                self.field.SetInsertionPoint(pos)
                wx._core.TextEntry.SetSelection(self.field, pos, self.field.LastPosition)
                break
        else:
            evt.Skip()


class TextBinding(object):
    def __init__(self, field, trait, readonly=False):
        self.field, self.trait = field, trait
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view(getattr(*trait))

        if not readonly:
            field.Bind(wx.EVT_TEXT, self.update_model)

    def update_view(self, new):
        if self.field.GetValue() != new:
            self.field.SetValue(new and unicode(new) or '')

    def update_model(self, event):
        value = self.field.GetValue()
        if getattr(*self.trait) != value:
            setattr(self.trait[0], self.trait[1], value)
        event.Skip()


class SliderBinding(object):
    def __init__(self, field, trait, readonly=False):
        self.field, self.trait = field, trait
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view(getattr(*trait))

        if not readonly:
            field.Bind(wx.EVT_SLIDER, self.update_model)

    def update_view(self, new):
        if self.field.GetValue() != new:
            self.field.SetValue(new)

    def update_model(self, event):
        value = self.field.GetValue()
        if getattr(*self.trait) != value:
            setattr(self.trait[0], self.trait[1], value)
        event.Skip()


class DateTimeBinding(object):
    def __init__(self, field, trait, readonly=False):
        self.field, self.trait = (field, trait)
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view(getattr(*trait))

        if not readonly:
            field.Bind(wx.EVT_TEXT, self.update_model)

    def update_view(self, new):
        if new:
            value = new.strftime(self.field._datetime_format)
            if self.field.GetValue() != new:
                self.field.SetValue(value)

    def update_model(self, event):
        value = self.field.GetDateTimeValue()
        if self.field.IsValid() and getattr(*self.trait) != value:
            setattr(self.trait[0], self.trait[1], value)
        event.Skip()


class DateBinding(object):
    def __init__(self, field, trait, readonly=False):
        self.field, self.trait = field, trait
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')

        # spinner always shows a date, so force a value for the trait
        value = getattr(*self.trait) or datetime.datetime.now()
        self.update_view(value)
        setattr(self.trait[0], self.trait[1], value)

        if not readonly:
            field.Bind(wx.EVT_DATE_CHANGED, self.update_model)

    def update_view(self, new):
        new = wx.DateTimeFromTimeT(time.mktime(new.timetuple()))
        if self.field.GetValue() != new:
            self.field.SetValue(new)

    def update_model(self, event):
        value = self.field.GetValue()
        value = datetime.datetime.fromtimestamp(value.GetTicks())
        if getattr(*self.trait) != value:
            setattr(self.trait[0], self.trait[1], value)
        event.Skip()


class FileBinding(object):
    def __init__(self, field, trait):
        self.field, self.trait = (field, trait)
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view(getattr(*trait))
        self.field.Bind(wx.EVT_FILEPICKER_CHANGED, self.update_model)

    def update_view(self, new):
        if self.field.GetPath() != new:
            self.field.SetPath(new)

    def update_model(self, event):
        new = event.GetPath()
        if new != getattr(*self.trait):
            setattr(self.trait[0], self.trait[1], new)
