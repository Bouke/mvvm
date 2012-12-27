from decimal import Decimal
import re
import wx
import wx.grid
import traits.api as traits

from mvvm.viewbinding import display
from mvvm.viewbinding.interactive import ChoiceBinding, ComboBinding


class GridBinding(object):
    """Binds a Grid to a Table

    Example code for saving a grid when closing the window:

        window.Bind(wx.EVT_CLOSE, close)

        def close(evt):
            if grid.IsCellEditControlEnabled():
                grid.SaveEditControlValue()
                grid.DisableCellEditControl()
                wx.CallAfter(window.Close)
                return evt.Veto()
            if not table.SaveGrid():
                return evt.Veto()
            evt.Skip()
    """
    def __init__(self, field, table, mapping=None, types=None, commit_on='row'):
        self.field = field
        self.table = table
        self.commit_on = commit_on
        self.mapping = [Column.init(col) for col in mapping or []]
        self.types = types or {}

        self.table = getattr(*table)
        self.table.mapping = self.mapping
        self.table.commit_on = commit_on
        self.table.grid = self.field
        self.field.SetTable(self.table)
        self.on_table_message()

        self.field.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)
        self.field.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)
        self.field.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        for type_k, type_v in self.types.items():
            self.field.RegisterDataType(type_k, type_v.renderer, type_v.editor)

        # Inject our table message listener
        process_table_message = self.field.ProcessTableMessage
        self.field.ProcessTableMessage = lambda message:\
            process_table_message(message) and self.on_table_message(message)

        self.veto_next_select_cell = False

    def on_table_message(self, message=None):
        # Only apply styles to the rows / cols
        for col_idx in range(self.table.GetNumberCols()):
            if col_idx < len(self.mapping):
                col = self.mapping[col_idx]
                if col.width is not None:
                    self.field.SetColSize(col_idx, col.width)

    def on_cell_changed(self, evt):
        if self.commit_on == 'cell':
            if not self.table.SaveCell(evt.Row, evt.Col):
                # Veto do_select_cell as that would in turn trigger
                # on_select_cell and re-run the savecell, and resulting in
                # the same error message.
                self.veto_next_select_cell = True
        # The grid does not always render the grid correctly when a dialog  was
        # shown, so it needs a `Refresh` for the active cell to be highlighted.
        self.field.Refresh()

    def do_select_cell(self, row, col):
        # See `on_cell_changed` on why this method can be `Veto`ed.
        if not self.veto_next_select_cell:
            self.field.SetGridCursor(row, col)
        self.veto_next_select_cell = False
        # The grid does not always render the grid correctly when a dialog  was
        # shown, so it needs a `Refresh` for the active cell to be highlighted.
        self.field.Refresh()

    def on_select_cell(self, evt):
        if self.commit_on == 'grid':
            return evt.Skip()

        from_ = (self.field.GetGridCursorRow(), self.field.GetGridCursorCol())
        to_ = (evt.Row, evt.Col)

        if self.field.IsCellEditControlEnabled():
            # @todo By inspecting the current value of the control, we can
            # check if the value is to be accepted; thus .Veto() before the
            # celleditor is actually disabled.
            self.field.SaveEditControlValue()
            self.field.DisableCellEditControl()
            wx.CallAfter(self.do_select_cell, *to_)
            return evt.Veto()

        elif self.commit_on == 'cell' and from_ != to_:
            # Try to save the cell, even though it will fail as on_cell_changed
            # will only handle the happy flow. Failing to save will show the
            # previous error message (again) and remembers the user of the
            # faulty input.
            if not self.table.SaveCell(*from_):
                return evt.Veto()

        elif self.commit_on == 'row' and from_[0] != to_[0]:
            if not self.table.SaveRow(from_[0]):
                return evt.Veto()

        elif self.commit_on == 'col' and from_[1] != to_[1]:
            if not self.table.SaveCol(from_[1]):
                return evt.Veto()

        evt.Skip()

    def on_key_down(self, event):
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_NUMPAD_DELETE):
            if self.field.GetSelectedRows():
                self.table.DeleteRows(self.field.GetSelectedRows())
                self.field.ClearSelection()
            else:
                # Remove the value of the current field if delete/backspace
                # was pressed when in viewing mode.
                self.table.SetValue(self.field.GridCursorRow,
                                    self.field.GridCursorCol, None)
                # Might need to save changes when commit_on = cell
                self.on_cell_changed(wx.grid.GridEvent(
                    self.field.GetId(), wx.grid.wxEVT_GRID_CELL_CHANGED,
                    self.field, self.field.GridCursorRow,
                    self.field.GridCursorCol))
            return
        elif event.GetKeyCode() in [wx.WXK_NUMPAD_ENTER, wx.WXK_RETURN]:
            # Need to stop cell editing first, saving the cell value before
            # trying to commit.
            #  * Normal: move cursor, commit, save cell
            #  * Desired: move cursor, save cell, commit
            self.field.SaveEditControlValue()
            self.field.DisableCellEditControl()

            # Create a new row after the current row. On success, move the
            # cursor to the left-most cell of the new row.
            if self.field.GridCursorRow == self.table.GetNumberRows() - 1:
                self.table.CreateRow()
            if self.field.GridCursorRow < self.table.GetNumberRows() - 1:
                self.field.SetGridCursor(self.field.GridCursorRow + 1, 0)
                self.field.MakeCellVisible(self.field.GridCursorRow, 0)

            # Move to the left-most cell of the next row.
            return

        event.Skip()


class Column(display.Column):
    def __init__(self, attribute, label, width=None, type_name=None):
        self.attribute = attribute
        self.label = label
        self.width = width
        self.type_name = type_name


class ChoiceType(object):
    class Trait(traits.HasTraits):
        value = traits.Any

    class Editor(wx.grid.PyGridCellEditor):
        def __init__(self, choices=None, provider=None):
            super(ChoiceType.Editor, self).__init__()
            self.trait = ChoiceType.Trait()
            self.choices = choices
            self.provider = provider

        def Create(self, parent, id, evtHandler):
            if self.provider:
                self.SetControl(wx.ComboBox(parent, id))
                self.binding = ComboBinding(self.GetControl(),
                                            (self.trait, 'value'),
                                            self.provider)
            else:
                self.SetControl(wx.Choice(parent, id))
                self.binding = ChoiceBinding(self.GetControl(),
                                             (self.trait, 'value'),
                                             self.choices)
            self.Control.PushEventHandler(evtHandler)

        def SetSize(self, rect):
            # Adjust for minimal height of the control
            height = self.GetControl().GetBestSize()[1]
            rect.y = rect.y + rect.height / 2 - max(rect.height, height) / 2
            rect.height = max(rect.height, height)
            super(ChoiceType.Editor, self).SetSize(rect)

        def BeginEdit(self, row, col, grid):
            value = grid.GetTable().GetValueAsObject(row, col)
            if self.provider:
                self.start_value = unicode(value or '')
                # First, unset previous selection. Otherwise the ComboBinding
                # would not start updating the choices when the Value is set.
                self.Control.Selection = -1
                self.Control.Value = self.start_value
                self.Control.SetInsertionPointEnd()
                self.Control.SelectAll()
            else:
                self.start_value = self.choices[value]
                self.Control.SetStringSelection(self.start_value)

            # Windows kills the control if the event handler is enabled, so
            # it needs to be temporarily disabled when setting the focus.
            if wx.Platform == '__WXMSW__':
                self.Control.EventHandler.SetEvtHandlerEnabled(False)

            self.GetControl().SetFocus()

            # Windows does not like having the popup opened while typing, so
            # only show it on OSX.
            if wx.Platform == '__WXMAC__' and self.provider:
                self.GetControl().Popup()

            if wx.Platform == '__WXMSW__':
                self.Control.EventHandler.SetEvtHandlerEnabled(True)

        def StartingKey(self, evt):
            # Post start key to control's event handler. Only the combobox
            # seems to care.
            self.Control.ProcessEvent(evt)

        def Reset(self):
            # Reset the control to the begin state, see BeginEdit.
            if self.provider:
                self.Control.Selection = -1
                self.Control.Value = self.start_value
            else:
                self.Control.SetStringSelection(self.start_value)

        def EndEdit(self, row, col, grid, prev):
            if self.provider:
                if self.Control.Value == self.start_value:
                    return
                if self.Control.Selection >= 0:
                    value = self.Control.GetClientData(self.Control.Selection)
                else:
                    value = None
            else:
                if self.Control.StringSelection == self.start_value:
                    return
                value = self.binding.choices.keys()[self.GetControl().Selection]
            grid.GetTable().SetValueAsObject(row, col, value)

    def __init__(self, choices=None, provider=None):
        self.trait = self.Trait()
        self.choices = choices
        self.provider = provider

        self.editor = self.Editor(choices=choices, provider=provider)
        self.renderer = wx.grid.GridCellStringRenderer()


class BoolType(object):
    class Editor(wx.grid.PyGridCellEditor):
        def Create(self, parent, id, evtHandler):
            self.SetControl(wx.CheckBox(parent, id))
            self.GetControl().PushEventHandler(evtHandler)

        def BeginEdit(self, row, col, grid):
            self.Control.Value = bool(grid.Table.GetValueAsObject(row, col))
            wx.CallAfter(grid.DisableCellEditControl)

        def StartingClick(self):
            self.Control.Value = not self.Control.Value

        def StartingKey(self, evt):
            if evt.KeyCode == wx.WXK_SPACE:
                self.Control.Value = not self.Control.Value
                return
            evt.Skip()

        def EndEdit(self, row, col, grid, prev):
            grid.Table.SetValueAsObject(row, col, self.Control.Value)

    def __init__(self):
        self.editor = self.Editor()
        self.renderer = wx.grid.GridCellBoolRenderer()


class TimeType(object):
    @staticmethod
    def time_to_text(time):
        return '%02d:%06.3f' % divmod(time, 60) if time is not None else ''

    class Editor(wx.grid.PyGridCellEditor):
        # Partly ported from wxGridCellTextEditor
        def Create(self, parent, id, evtHandler):
            style = wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB|wx.NO_BORDER
            if wx.Platform == '__WXMSW__':
                style |= wx.TE_RICH2
            self.Control = wx.TextCtrl(parent, id, style=style)
            self.Control.PushEventHandler(evtHandler)

        def SetSize(self, rect):
            if wx.Platform == '__WXMSW__':
                rect.x += 2 if rect.x == 0 else 3
                rect.y += 2 if rect.y == 0 else 3
                rect.width -= 2
                rect.height -= 2
            super(TimeType.Editor, self).SetSize(rect)

        def BeginEdit(self, row, col, grid):
            self.start_value = grid.Table.GetValueAsObject(row, col)
            self.Control.Value = TimeType.time_to_text(self.start_value)
            self.Control.SetInsertionPointEnd()
            self.Control.SelectAll()
            self.Control.SetFocus()

        def Reset(self):
            self.Control.Value = TimeType.time_to_text(self.start_value)
            self.Control.SetInsertionPointEnd()

        def EndEdit(self, row, col, grid, prev):
            text = self.Control.Value
            m = re.match(r'([0-9]{0,2})[ .:]?([0-9]{2})(([0-9]{3})|[. ]([0-9]{1,3}))', text)
            if not m:
                return False

            value = Decimal('%s.%s' % (m.group(2), m.group(4) or m.group(5)))
            value += int(m.group(1) or 0) * 60

            if value == self.start_value:
                return False

            grid.Table.SetValueAsObject(row, col, value)

        def StartingKey(self, evt):
            key = evt.UnicodeKey
            if key == wx.WXK_DELETE:
                self.Control.Remove(0, 1)
            elif key == wx.WXK_BACK:
                pos = self.Control.GetLastPosition()
                self.Control.Remove(pos-1, pos)
            else:
                self.Control.WriteText(unichr(key))

    class Renderer(wx.grid.PyGridCellRenderer):
        def Draw(self, grid, attr, dc, rect, row, col, isSelected):
            # Ported from https://github.com/wxWidgets/wxWidgets/blob/master/src/generic/gridctrl.cpp#L50
            fg = grid.SelectionForeground
            if grid.Enabled:
                if isSelected:
                    if grid.HasFocus():
                        bg = grid.SelectionBackground
                    else:
                        bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
                else:
                    bg = attr.BackgroundColour
                    fg = attr.TextColour
            else:
                bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)

            dc.SetClippingRect(rect)
            dc.SetFont(attr.GetFont())
            dc.SetTextBackground(bg)
            dc.SetTextForeground(fg)
            dc.SetBrush(wx.Brush(bg, wx.SOLID))
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangleRect(rect)

            value = grid.Table.GetValueAsObject(row, col)
            text = '%02d:%06.3f' % divmod(value, 60) if value is not None else ''

            width, height = dc.GetTextExtent(text)
            x = rect.x + max(rect.width - width, 4) - 2
            dc.DrawText(text, x, rect.y+1)

            if width > rect.width-2:
                width, height = dc.GetTextExtent(u'\u2026')
                x = rect.x+1 + rect.width-2 - width
                dc.DrawRectangle(x, rect.y+1, width+1, height)
                dc.DrawText(u'\u2026', x, rect.y+1)

            dc.DestroyClippingRegion()

    def __init__(self):
        self.editor = self.Editor()
        self.renderer = self.Renderer()
