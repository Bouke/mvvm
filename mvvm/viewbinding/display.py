import wx


class ShowBinding(object):
    def __init__(self, field, instance, trait, show_if_value=True):
        self.field, self.instance, self.trait, self.show_if_value = (
            field, instance, trait, show_if_value)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        value = getattr(self.instance, self.trait)
        if type(self.show_if_value) == bool:
            value = bool(value)
        self.field.Show(value == self.show_if_value)
        self.field.GetParent().GetSizer().Layout()

        # resize frame if @min_best_size'd
        if hasattr(self.field.TopLevelParent, 'MinBestSize'):
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


class ListBinding(object):
    def __init__(self, field, instance, trait, mapping):
        self.field, self.instance, self.trait, self.mapping = (
            field, instance, trait, mapping)

        for col_idx, attribute in enumerate(mapping):
            field.InsertColumn(col_idx, *attribute[1:])
        self.update_view()

        # sync with grid.py[196:208]
        def items_listener(new):
            for row_idx, row in enumerate(new.added):
                self.insert_row(new.index+row_idx, row)
            for row_idx, row in enumerate(new.removed):
                self.remove_row(new.index+row_idx)
        def trait_listener(tl_instance, tl_trait, tl_value):
            if tl_instance == instance:
                self.update_view()
            else:
                self.update_row(getattr(instance, trait).index(tl_instance),
                    tl_instance)
        instance.on_trait_change(items_listener, trait+'_items', dispatch='ui')
        instance.on_trait_change(trait_listener, trait+'.+', dispatch='ui')

        if hasattr(instance, trait+'_selection'):
            field.Bind(wx.EVT_LIST_ITEM_SELECTED, self.selection_changed)
            field.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.selection_changed)

    def update_view(self):
        self.field.TopLevelParent.Freeze()
        self.field.DeleteAllItems()
        for row_idx, row in enumerate(getattr(self.instance, self.trait)):
            self.insert_row(row_idx, row)
        self.field.TopLevelParent.Thaw()

        # Fire faux selection as the selection probably changed
        self.selection_changed(None)

    def insert_row(self, pos, row):
        self.field.InsertStringItem(pos, '')
        self.update_row(pos, row)

    def update_row(self, pos, row):
        for col_idx, attribute in enumerate(self.mapping):
            attribute = attribute[0]
            disp_attr = 'get_%s_display' % attribute
            if hasattr(row, disp_attr) and callable(getattr(row, disp_attr)):
                value = getattr(row, disp_attr)()
            else:
                value = getattr(row, attribute)
            self.field.SetStringItem(pos, col_idx, unicode(value or ''))

    def remove_row(self, pos):
        self.field.DeleteItem(pos)

    def selection_changed(self, event):
        selection = []
        index = self.field.GetFirstSelected()
        while index != -1:
            selection.append(getattr(self.instance, self.trait)[index])
            index = self.field.GetNextItem(index, wx.LIST_NEXT_ALL,
                                           wx.LIST_STATE_SELECTED)
        setattr(self.instance, self.trait+'_selection', selection)
        if event: event.Skip()


class LabelBinding(object):
    def __init__(self, field, instance, trait):
        self.field, self.instance, self.trait = (
            field, instance, trait)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        self.field.SetLabel(str(getattr(self.instance, self.trait)))


class StatusBarBinding(object):
    def __init__(self, field, instance, trait, field_number):
        self.field, self.instance, self.trait, self.field_number = (
            field, instance, trait, field_number)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        self.field.SetStatusText(getattr(self.instance, self.trait),
            self.field_number)


class TitleBinding(object):
    def __init__(self, field, instance, trait):
        self.field, self.instance, self.trait = (field, instance, trait)
        instance.on_trait_change(self.update_view, trait, dispatch='ui')
        self.update_view()

    def update_view(self):
        self.field.SetTitle(str(getattr(self.instance, self.trait)))
