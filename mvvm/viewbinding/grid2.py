import wx.grid
from mvvm.viewbinding import display


class Column(display.Column):
    def __init__(self, attribute, label, width=None, editor=None, h_align=None,
                 v_align=None):
        super(Column, self).__init__(attribute, label, width, h_align)
        self.attribute = attribute
        self.label = label
        self.width = width
        self.editor = editor
        self.v_align = v_align


class GridBinding(object):
    """Binds a Grid to a Table

    Example code for saving a grid when closing the window:

        window.Bind(wx.EVT_CLOSE, close)

        def close(evt):
            if grid.IsCellEditControlEnabled():
                grid.DisableCellEditControl()
                wx.CallAfter(window.Close)
                return evt.Veto()
            if not table.SaveGrid():
                return evt.Veto()
            evt.Skip()
    """
    def __init__(self, field, trait, mapping, commit_on='row'):
        self.field = field
        self.trait = trait
        self.commit_on = commit_on
        self.mapping = [Column.init(col) for col in mapping]

        self.table = getattr(trait[0], trait[1]+"_table")
        self.table.mapping = self.mapping
        self.table.commit_on = commit_on
        self.field.SetTable(self.table)

        self.field.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)
        self.field.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)

        self.field.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.veto_next_select_cell = False

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
            self.field.DisableCellEditControl()

            # Create a new row after the current row. On success, move the
            # cursor to the left-most cell of the new row.
            if self.field.GridCursorRow == self.table.GetNumberRows() - 1:
                self.table.CreateRow()
            self.field.SetGridCursor(self.field.GridCursorRow + 1, 0)
            self.field.MakeCellVisible(self.field.GridCursorRow, 0)

            # Move to the left-most cell of the next row.
            return

        event.Skip()
