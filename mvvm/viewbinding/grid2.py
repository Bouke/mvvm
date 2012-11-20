import wx.grid

class GridBinding(object):
    def __init__(self, field, trait, mapping, commit_on='grid'):
        self.field = field
        self.trait = trait
        self.table = getattr(trait[0], trait[1]+"_table")
        self.table.mapping = mapping
        self.commit_on = commit_on

#        self._mapping = mapping
        self.field.SetTable(self.table)

        self.field.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)

        self._pending_select = None

    def do_select_cell(self, row, col):
        self.field.SetGridCursor(row, col)
        self.field.Refresh() # current cell might not be highlighted

    def on_select_cell(self, evt):
        if self.commit_on == 'grid':
            return evt.Skip()

        from_ = (self.field.GetGridCursorRow(), self.field.GetGridCursorCol())
        to_ = (evt.Row, evt.Col)

        if self.field.IsCellEditControlEnabled():
            self.field.DisableCellEditControl()
            wx.CallAfter(self.do_select_cell, *to_)
            return evt.Veto()

        if self.commit_on == 'cell' and from_ != to_:
            if not self.table.SaveRow(from_[0]):
                return evt.Veto()

        if self.commit_on == 'row' and from_[0] != to_[0]:
            if not self.table.SaveRow(from_[0]):
                return evt.Veto()

        evt.Skip()
