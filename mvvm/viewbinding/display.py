import time
import wx


class ShowBinding(object):
    def __init__(self, field, trait, show_if_value=True):
        self.field, self.trait, self.show_if_value = field, trait, show_if_value
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view()

    def update_view(self):
        value = getattr(*self.trait)
        if type(self.show_if_value) == bool:
            value = bool(value)
        self.field.Show(value == self.show_if_value)
        self.field.GetParent().GetSizer().Layout()

        # resize frame if @min_best_size'd
        if hasattr(self.field.TopLevelParent, 'MinBestSize'):
            # First, invalidate all parents
            parent = self.field.Parent
            while parent:
                parent.InvalidateBestSize()
                parent = parent.Parent
            self.field.TopLevelParent.SetSize(
                self.field.TopLevelParent.MinBestSize())


class EnabledBinding(object):
    def __init__(self, field, instance, trait, enabled_if_value=True):
        self.field, self.instance, self.trait, self.enabled_if_value = (
            field, instance, trait, enabled_if_value)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        value = getattr(self.instance, self.trait)
        # True-ish / False-ish
        if self.enabled_if_value == True or self.enabled_if_value == False:
            value = bool(value)
        self.field.Enable(value == self.enabled_if_value)


class FocusBinding(object):
    def __init__(self, field, instance, trait, focus_if_value=True):
        self.field, self.instance, self.trait, self.focus_if_value = (
            field, instance, trait, focus_if_value)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        if getattr(self.instance, self.trait) == self.focus_if_value:
            self.field.SetFocus()


class Column(object):
    def __init__(self, attribute, label, width=-1, align=0):
        self.attribute = attribute
        self.label = label
        self.width = width
        self.align = align

    @classmethod
    def init(cls, args):
        if isinstance(args, cls):
            return args
        return cls(*args)


class ListBinding(object):
    def __init__(self, field, trait, mapping):
        self.field, self.trait = field, trait
        mapping = [Column.init(col) for col in mapping]
        self.table = getattr(trait[0], trait[1]+"_table")
        self.table.mapping = mapping
        self.table.ResetView = self.update_values
        self.table.UpdateValues = self.update_values

        assert self.field.on_get_item_text, 'Cannot override on_get_item_text'
        assert self.field.HasFlag(wx.LC_VIRTUAL), 'Field is not virtual'
        self.field.on_get_item_text = self.on_get_item_text
        for col_idx, col in enumerate(mapping):
            self.field.InsertColumn(col_idx, col.label, col.align, col.width)

        self.update_values()
        field.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_view_selection_changed)
        field.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_view_selection_changed)
        trait[0].on_trait_change(self.on_model_selection_changed,
                                 trait[1]+'_selection[]')

    def update_values(self):
        self.field.SetItemCount(self.table.GetNumberRows())

    def on_get_item_text(self, row_idx, col_idx):
        return self.table.GetValue(row_idx, col_idx)

    def get_selected_indexes(self):
        indexes = set()
        row_idx = self.field.GetFirstSelected()
        while row_idx != -1:
            indexes.add(row_idx)
            row_idx = self.field.GetNextSelected(row_idx)
        return indexes

    def on_view_selection_changed(self, event):
        setattr(self.trait[0], self.trait[1]+'_selection',
                [self.table.GetRow(idx) for idx in self.get_selected_indexes()])
        event.Skip()

    def on_model_selection_changed(self, new):
        cur = self.get_selected_indexes()
        new = set([self.table.GetRowIndex(obj) for obj in new])
        for idx in cur-new:  # deselect
            self.field.SetItemState(idx, 0, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)
        for idx in new-cur:  # select
            self.field.SetItemState(idx, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)


class LabelBinding(object):
    def __init__(self, field, trait):
        self.field, self.trait = field, trait
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view()

    def update_view(self):
        self.field.SetLabel(unicode(getattr(*self.trait)))


class StatusBarBinding(object):
    def __init__(self, field, trait, field_number):
        self.field, self.trait, self.field_number = (field, trait, field_number)
        trait[0].on_trait_change(self.update_view, trait[1], dispatch='ui')
        self.update_view()

    def update_view(self):
        self.field.SetStatusText(getattr(*self.trait),
            self.field_number)


class TitleBinding(object):
    def __init__(self, field, instance, trait):
        self.field, self.instance, self.trait = (field, instance, trait)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        self.field.SetTitle(str(getattr(self.instance, self.trait)))
