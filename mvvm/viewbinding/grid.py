from __future__ import absolute_import

import wx
import wx.grid
from traits.api import HasTraits, Any

from mvvm.viewbinding import ComboBinding, ChoiceBinding


class Col(object):
    # getter can be a attribute name or callback, if callback, also specify
    # setter callback
    def __init__(self, label, getter, setter=None, width=None, editor=None):
        self.label, self.getter, self.setter, self.width, self.editor = (
            label, getter, setter, width, editor)

    def get(self, object):
        return getattr(object, self.getter)

    def set(self, object, value):
        setattr(object, self.getter, value)


class Choice(object):
    class Trait(HasTraits):
        value = Any

    def __init__(self, choices_or_provider):
        self.trait = Choice.Trait()
        self.choices_or_provider = choices_or_provider
        self.editor = wx.grid.GridCellChoiceEditor([],
            hasattr(choices_or_provider, 'get_choices'))

    def on_editor_shown(self, event, value):
        # When the control is shown (start editing), remove all items left from
        # previous editing (on other row/cell)
        self.trait.value = value
        if hasattr(self, 'control') and hasattr(self.choices_or_provider, 'get_choices'):
            while not self.control.IsEmpty():
                self.control.Delete(0)

    def on_editor_created(self, event):
        self.control = event.GetControl()
        if hasattr(self.choices_or_provider, 'get_choices'):
            self.binding = ComboBinding(self.control, self.trait, 'value',
                self.choices_or_provider)
        else:
            self.binding = ChoiceBinding(self.control, self.trait, 'value',
                self.choices_or_provider)
        self.control.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter)

    def on_text_enter(self, event):
        grid = event.EventObject.GrandParent
        grid.DisableCellEditControl()
        grid.SetFocus()

    def get_display_text(self, data):
        if hasattr(self.choices_or_provider, 'get_display_text'):
            return self.choices_or_provider.get_display_text(data)
        else:
            return self.choices_or_provider.get(data, '')

    def get_data(self):
        if self.control.Selection != -1:
            return self.control.GetClientData(self.control.Selection)
        return self.trait.value


class EditableBinding(object):
    def __init__(self, field, instance, trait, mapping):
        self.field, self.instance, self.trait, self.mapping = (
            field, instance, trait, mapping)

        # Add empty row if empty object set.
        creator = getattr(instance, trait+'_create', None)
        if callable(creator) and not getattr(instance, trait):
            new_row = creator()
            if new_row:
                getattr(instance, trait).append(new_row)

        # Create column labels.
        field.InsertCols(0, len(mapping), False)
        for col_idx, col in enumerate(mapping):
            field.SetColLabelValue(col_idx, col.label)
            if col.width: field.SetColSize(col_idx, col.width)

        self.update_view()

        def on_editor_created(event):
            col = mapping[event.GetCol()]
            if col.editor:
                col.editor.on_editor_created(event)
            event.Skip()
        field.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, on_editor_created)

        # Setting changed values to the underlying object.  There are two
        # variants responsible for this setting, the first when there is an
        # explicit editor present for a column else the second.
        # Also, if a user enters an invalid value, this value is not stored in
        # the first. The second will always read the value from the object, so
        # the previous value will be restored.
        def set(col, event, value):
            object = getattr(self.instance, self.trait)[event.GetRow()]
            col.set(object, value)
        def on_editor_shown(event):
            col = mapping[event.GetCol()]
            if col.editor:
                value = col.get(self.get_object(event.GetRow()))
                col.editor.on_editor_shown(event, value)
            event.Skip()
        def on_editor_hidden(event):
            col = mapping[event.GetCol()]
            if col.editor:
                value = col.editor.get_data()
                if value:
                    set(col, event, value)
            event.Skip()
        def on_cell_change(event):
            col = mapping[event.GetCol()]
            if not col.editor:
                set(col, event, field.GetCellValue(event.GetRow(), event.GetCol()))
            else:
                field.SetCellValue(event.GetRow(), event.GetCol(),
                    col.editor.get_display_text(
                        col.get(self.get_object(event.GetRow())
                    )))
            event.Skip()
        field.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, on_editor_shown)
        field.Bind(wx.grid.EVT_GRID_EDITOR_HIDDEN, on_editor_hidden)
        field.Bind(wx.grid.EVT_GRID_CELL_CHANGED, on_cell_change)

        # When switching to another row, the previous row will be committed
        # to the database
        self.current_row = 0
        def commit(row):
            object = getattr(self.instance, self.trait)[row]
            has_changes = getattr(object, 'has_changes')
            if callable(has_changes): has_changes = has_changes()
            if not has_changes: return True
            return getattr(instance, trait+'_save')(object)

        def on_cell_select(event):
            if event.GetRow() != self.current_row:
                # Try to commit the row. If this fails, change the background color
                # of the cell and move the cursor back into the row.
                success = commit(self.current_row)
                bg_color = field.GetDefaultCellBackgroundColour()
                if not success:
                    bg_color = 'RED'
                    event.Veto()
                for col_idx in range(0,len(mapping)):
                    field.SetCellBackgroundColour(self.current_row, col_idx, bg_color)
                # Refresh is required when Vetoing
                field.ForceRefresh()
            if event.IsAllowed():
                self.current_row = event.GetRow()
            event.Skip()
        field.Bind(wx.grid.EVT_GRID_SELECT_CELL, on_cell_select)

        def on_key_down(event):
            if event.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_BACK,
                                      wx.WXK_NUMPAD_DELETE]:
                if field.GetSelectedRows():
                    getattr(instance, trait+'_delete')(
                        [self.get_object(idx) for idx in field.GetSelectedRows()])
                else:
                    # Remove the value of the current field if delete/backspace
                    # was pressed when in viewing mode.
                    row_idx = field.GetGridCursorRow()
                    col_idx = field.GetGridCursorCol()
                    col = mapping[col_idx]
                    field.SetCellValue(row_idx, col_idx, '')
                    col.set(self.get_object(row_idx), None)
                return

            elif event.GetKeyCode() in [wx.WXK_NUMPAD_ENTER, wx.WXK_RETURN]:
                # Need to stop cell editing first, saving the cell value before
                # trying to commit.
                #  * Normal: move cursor, commit, save cell
                #  * Desired: move cursor, save cell, commit
                field.DisableCellEditControl()

                row_idx = field.GetGridCursorRow()

                # Create a new row and append it to the object list if a new
                # row was returned. If None is returned, no new row is created.
                objects = getattr(instance, trait)
                if row_idx == len(objects) - 1 and callable(creator):
                    new_row = creator()
                    if not new_row: return
                    objects.append(new_row)

                # Move to the left-most cell of the next row.
                field.SetGridCursor(row_idx + 1, 0)
                field.MakeCellVisible(row_idx + 1, 0)
                return

            event.Skip()
        field.Bind(wx.EVT_KEY_DOWN, on_key_down)

        # sync with display.py[61:73]
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


    def get_object(self, row):
        return getattr(self.instance, self.trait)[row]

    def update_view(self):
        self.field.DeleteRows(0, self.field.GetNumberRows(), False)
        for row_idx, row in enumerate(getattr(self.instance, self.trait)):
            self.insert_row(row_idx, row)

    def insert_row(self, pos, row):
        assert hasattr(row, 'has_changes'), 'row should have a `has_changes`'

        cursor_row = self.field.GetGridCursorRow()
        if pos <= cursor_row:
            self.field.DisableCellEditControl()

        self.field.InsertRows(pos)
        self.field.SetRowLabelValue(pos, '')
        for col_idx, col in enumerate(self.mapping):
            if col.editor:
                # editor C++ would be destroyed if no rows left
                # https://groups.google.com/d/msg/wxpython-users/ZcxAc6P4-n0/T7LoW3yLWloJ
                col.editor.editor.IncRef()

                self.field.SetCellEditor(pos, col_idx, col.editor.editor)
        self.update_row(pos, row)

        if pos <= cursor_row and (cursor_row + 1) < self.field.GetNumberRows():
            self.current_row += 1
            self.field.MoveCursorDown(False)

    def update_row(self, row_idx, row):
        editing = self.field.IsCellEditControlShown()
        cursor = self.field.GetGridCursorRow(), self.field.GetGridCursorCol()
        for col_idx, col in enumerate(self.mapping):
            # Do not update the cell that is currently being edited, otherwise
            # strange results might happen. In the case of GridCellChoiceEditor
            # a dropdown will be shown regardless of the editor state; the
            # editor might be in the process of being hidden.
            if editing and (row_idx, col_idx) == cursor: continue
            value = col.get(row)
            if col.editor: value = col.editor.get_display_text(value)
            self.field.SetCellValue(row_idx, col_idx, unicode(value or ''))

    def remove_row(self, pos):
        cursor_row = self.field.GetGridCursorRow()
        if pos <= cursor_row:
            self.field.DisableCellEditControl()
        self.field.DeleteRows(pos, 1, False)
        if pos <= cursor_row and cursor_row > 0:
            self.current_row -= 1
            self.field.MoveCursorUp(False)
