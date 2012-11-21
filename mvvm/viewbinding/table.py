import traits.api as traits
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
    def __init__(self, trait, mapping=None):
        super(ListTable, self).__init__()
        self._trait = trait
        self.mapping = mapping
        self.saver = getattr(self._trait[0], '%s_save' % self._trait[1], None)
        self._setup()

    def _setup(self):
        self._trait[0].on_trait_change(self._trait_listener,
                                       self._trait[1]+'.+', dispatch='ui')
        self._trait[0].on_trait_change(self._items_listener,
                                       self._trait[1]+'_items', dispatch='ui')

    def _trait_listener(self, tl_instance, tl_trait, tl_value):
        if tl_instance == self._trait[0]:
            return self._items_listener()
        self.UpdateValues()

    def _items_listener(self):
        self.ResetView()

    def GetNumberRows(self):
        return len(getattr(*self._trait))

    def GetRowLabelValue(self, row_idx):
        return ''

    def GetNumberCols(self):
        return len(self.mapping)

    def GetColLabelValue(self, col_idx):
        return self.mapping[col_idx][1]

    def GetValue(self, row_idx, col_idx):
        attribute = self.mapping[col_idx][0]
        row = self.GetRow(row_idx)
        disp_attr = 'get_%s_display' % attribute
        if hasattr(row, disp_attr) and callable(getattr(row, disp_attr)):
            return getattr(row, disp_attr)()
        return getattr(row, attribute)

    def GetRow(self, row_idx):
        return getattr(*self._trait)[row_idx]

    def GetRowIndex(self, object):
        return getattr(*self._trait).index(object)

    def SetValue(self, row_idx, col_idx, value):
        attribute = self.mapping[col_idx][0]
        row = self.GetRow(row_idx)
        setattr(row, attribute, value)

    def SaveCell(self, row_idx, col_idx):
        return self.SaveRow(row_idx)

    def SaveRow(self, row_idx):
        row = self.GetRow(row_idx)
        if not row.has_changes: return True
        return self.saver([row])

    def SaveCol(self, col_idx):
        raise NotImplementedError()

    def SaveGrid(self):
        return self.saver(getattr(*self._trait))


class QueryTable(ListTable):
    class Cache(traits.HasTraits):
        rows = traits.Dict(traits.Int, traits.HasTraits)

    def _setup(self):
        self._cache = self.Cache()
        self._update_cache()
        self.page_size = 50
        self._trait[0].on_trait_change(self.reload, '%s_query' % self._trait[1])
        self._cache.on_trait_change(self.UpdateValues, 'rows.+')
        self.wrapper = wrap

    def _update_cache(self):
        self._query = getattr(self._trait[0], '%s_query' % self._trait[1])
        self._query.session = wx.GetApp().session
        self._cache.rows = {}
        self._num_rows = self._query.count()

    def reload(self):
        self._update_cache()
        self.UpdateValues()

    def _assert_in_cache(self, row_idx):
        if row_idx in self._cache.rows:
            return

        start = max(row_idx-self.page_size, 0)
        stop = min(row_idx+self.page_size, self._num_rows)

        for idx, row in enumerate(self._query[start:stop]):
            if start+idx not in self._cache.rows:
                self._cache.rows[start+idx] = self.wrapper(row)

    def GetNumberRows(self):
        return self._num_rows

    def GetRow(self, row_idx):
        self._assert_in_cache(row_idx)
        return self._cache.rows[row_idx]

    def GetRowIndex(self, object):
        for idx, row in self._cache.rows.iteritems():
            if row == object:
                return idx
        raise IndexError('object was not in cache')

    def SaveGrid(self):
        return self.saver(self._cache.rows.values())
