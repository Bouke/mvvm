from __future__ import absolute_import
import sys

import wx
from wx.lib.pubsub import pub
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.orm import Query
from traits.has_traits import HasTraits, on_trait_change
from traits.trait_types import List as TList, Instance, Str, Any
from traits.traits import Property

from mvvm.viewbinding.table import ListTable, QueryTable
from mvvm.viewmodel.util import CloseMixin
from mvvm.viewbinding.command import Command
from mvvm.viewmodel.wrapper import wrap, unwrap


class List(CloseMixin, HasTraits):
    """
    ViewModel for binding to a List View

    `Model` class that should be queried for objects.

    `objects` complete set of objects

    `objects_selection` objects currently selected by the user

    `del_cmd` command to execute to the delete the currently selected objects
        from persistent storage.

    `title` name of the window title, used in Generic Views, defaults to the
        class name of the Model + 's'
    """
    Model = None
    mapping = None

    autocommit = True
    pending_commit = TList(HasTraits)

    objects = TList(HasTraits)
    objects_selection = TList(HasTraits)
    objects_table = Instance(ListTable)

    del_cmd = Instance(Command)

    title = Str

    def create_query(self):
        return Query(self.Model)

    def _objects_default(self):
        query = self.create_query()
        query.session = wx.GetApp().session
        return [wrap(obj) for obj in query]

    @on_trait_change('objects_selection')
    def _on_selection_changed(self, sel):
        self.del_cmd.can_execute = bool(len(sel))

    def _del_cmd_default(self):
        return Command(self._on_del, False)

    def _on_del(self):
        self.objects_delete(self.objects_selection)
        self.objects_selection = []

    def _title_default(self):
        return self.Model.__name__ + 's'

    def objects_create(self):
        return wrap(self.Model())

    def _objects_do_delete(self, objects):
        session = wx.GetApp().session
        for object in objects:
            session.delete(object._wrapped)
        try:
            session.commit()
            return True
        except (AssertionError, IntegrityError) as e:
            session.rollback()
            # @todo error.user, not a database error
            pub.sendMessage('error.database', message=e.message,
                            exc_info=sys.exc_info())
            return False

    def objects_delete(self, objects):
        if self._objects_do_delete(objects):
            for object in objects:
                self.objects.remove(object)

    def objects_save(self, object):
        # @todo handle unwrite when database error, to leave the object in
        #       a valid (previous) state
        try:
            object.flush()
            if self.autocommit:
                self.objects_commit(object)
            else:
                self.pending_commit.append(object)
        except (IntegrityError, AssertionError) as e:
            wx.GetApp().session.rollback()
            # @todo error.user, not a database error
            pub.sendMessage('error.database', message=e.message,
                exc_info=sys.exc_info())
            return False
        return True

    def objects_commit(self, object):
        wx.GetApp().session.add(unwrap(object))
        wx.GetApp().session.commit()
        object.changes.clear()

    def _objects_table_default(self):
        return ListTable((self, 'objects'), self.mapping)

    @on_trait_change('objects.+,objects_items')
    def on_table_update(self):
        wx.CallAfter(self.objects_table.ResetView)


class ListSearchMixin(HasTraits):
    search = Str

    def __init__(self, **kwargs):
        super(ListSearchMixin, self).__init__(**kwargs)
        self.on_trait_change(self.do_search, 'search', dispatch='new')

    def do_search(self, search):
        if search:
            self.objects_query = self.create_search_query('%%%s%%' % search)
        else:
            self.objects_query = self.create_query()

    def create_search_query(self, search):
        raise NotImplementedError


class QueryList(List):
    objects_query = Instance(Query)

    def __init__(self, **kwargs):
        super(QueryList, self).__init__(**kwargs)
        self.remove_trait('objects')

    def _objects_default(self):
        return []

    def _objects_query_default(self):
        return self.create_query()

    def _objects_table_default(self):
        return QueryTable((self, 'objects_query'), self.mapping)

    def objects_delete(self, objects):
        if self._objects_do_delete(objects):
            self.objects_table.on_query_change()


class Detail(CloseMixin, HasTraits):
    """
    ViewModel for binding to a Detail View

    `object` is a property, it gets `_object_proxy` and sets `_object_original`.
        Normally, this property is all you need. If you would like to get your
        hands dirty, have a look at the `_object_*` variables.

    `_object_original` is the original object, in the state it was passed to
        the ViewModel.

    `_object_unwrapped` is the original object, but stripped from any wrappers.

    `_object_proxy` is the unwrapped object, but with a (new) wrapper to
        store changes to the object while it is being edited by the user.

    `save_cmd` command to execute when the changes made by the user should be
        persisted.

    `cancel_cmd` command to execute when the changes made by the user should not
        be persisted.

    `title` name of the window title, used in Generic Views, defaults to the
        class name of the unwrapped object.
    """
    object = Property(depends_on='[_object_proxy,_object_original]')
    _object_original = Any
    _object_unwrapped = Any
    _object_proxy = Instance(HasTraits)

    save_cmd = Instance(Command)
    cancel_cmd = Instance(Command)

    title = Str

    def commit(self):
        try:
            self._object_proxy.flush()
            wx.GetApp().session.add(self._object_unwrapped)
            wx.GetApp().session.commit()
        except (AssertionError, DatabaseError) as e:
            wx.GetApp().session.rollback()
            pub.sendMessage('error.database', message=e.message,
                exc_info=sys.exc_info())
            return False
        # Write changes back to the object passed in by the constructor
        for attr, value in self._object_proxy.changes.items():
            setattr(self._object_original, attr, value)
        # Reset changes
        self._object_proxy.changes.clear()
        return True

    def _save_cmd_default(self):
        def save():
            if self.commit():
                self.close = self.save_cmd
        return Command(save)

    def _cancel_cmd_default(self):
        def cancel():
            self.close = self.cancel_cmd
        return Command(cancel)

    def _get_object(self):
        if not self._object_proxy: raise NotImplementedError
        return self._object_proxy

    def _set_object(self, object):
        self._object_original = object

        bare = unwrap(object)
        self._object_unwrapped = bare
        self._object_proxy = bare and wrap(bare, False) or None

    def _title_default(self):
        return self._object_unwrapped.__class__.__name__
