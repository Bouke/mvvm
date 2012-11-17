from traits.has_traits import HasTraits
import wx
from wx.grid import PyGridTableBase
import model
from mvvm.viewmodel.wrapper import wrap


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


class ListTable(PyGridTableBase, TableHelperMixin):
    def __init__(self, trait, mapping):
        super(ListTable, self).__init__()
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
        row = self.GetRow(row_idx)
        disp_attr = 'get_%s_display' % attribute
        if hasattr(row, disp_attr) and callable(getattr(row, disp_attr)):
            return getattr(row, disp_attr)()
        return getattr(row, attribute)

    def GetRow(self, row_idx):
        return getattr(*self._trait)[row_idx]

    def GetRowIndex(self, object):
        return getattr(*self._trait).index(object)


class QueryTable(ListTable):
    def __init__(self, query, mapping):
        super(ListTable, self).__init__()
        self._query = query
        self._mapping = mapping
        self.update_cache()
        self.page_size = 50
        query[0].on_trait_change(self.on_query_change, query[1])

    def update_cache(self):
        query = getattr(*self._query)
        query.session = model.DBSession()
        self._rows_cache = {}
        self._num_rows = query.count()

    def on_query_change(self):
        self.update_cache()
        self.UpdateValues()

    def assert_in_cache(self, row_idx):
        if row_idx in self._rows_cache:
            return

        query = getattr(*self._query)
        query.session = model.DBSession()

        start = max(row_idx-self.page_size, 0)
        stop = min(row_idx+self.page_size, self._num_rows)

        for idx, row in enumerate(query[start:stop]):
            if start+idx not in self._rows_cache:
                self._rows_cache[start+idx] = wrap(row)

    def GetNumberRows(self):
        return self._num_rows

    def GetRow(self, row_idx):
        self.assert_in_cache(row_idx)
        return self._rows_cache[row_idx]

    def GetRowIndex(self, object):
        for idx, row in self._rows_cache.iteritems():
            if row == object:
                return idx
        raise IndexError('object was not in cache')
