import wx
from wx.grid import PyGridTableBase


class TableHelperMixin(object):
    def ResetView(self):
        """Trim/extend the control's rows and update all values"""
        grid = self.GetView()
        grid.BeginBatch()
        changes = [
            (grid.GetNumberRows(), self.GetNumberRows(),
             wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,
             wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (grid.GetNumberCols(), self.GetNumberCols(),
             wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED,
             wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
            ]
        for current, new, delmsg, addmsg in changes:
            if new < current:
                msg = wx.grid.GridTableMessage(self, delmsg, new, current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(self, addmsg, new-current)
                grid.ProcessTableMessage(msg)
        self.UpdateValues()
        grid.EndBatch()

    def UpdateValues( self ):
        """Update all displayed values"""
        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)


class ModelTable(PyGridTableBase, TableHelperMixin):
    def __init__(self, trait, mapping):
        super(ModelTable, self).__init__()
        self._trait = trait
        self._mapping = mapping

    def GetNumberRows(self):
        return len(getattr(*self._trait))

    def GetRowLabelValue(self, row_idx):
        return ''

    def GetNumberCols(self):
        return len(self._mapping)

    def GetColLabelValue(self, col_idx):
        return self._mapping[col_idx][1]

    def GetValue(self, row_idx, col_idx):
        attribute = self._mapping[col_idx][0]
        row = getattr(*self._trait)[row_idx]
        disp_attr = 'get_%s_display' % attribute
        if hasattr(row, disp_attr) and callable(getattr(row, disp_attr)):
            return getattr(row, disp_attr)()
        return getattr(row, attribute)

    def GetRow(self, row_idx):
        return getattr(*self._trait)[row_idx]

    def GetRowIndex(self, object):
        return getattr(*self._trait).index(object)
