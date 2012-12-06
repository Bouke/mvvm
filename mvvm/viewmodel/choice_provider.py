from __future__ import absolute_import

import wx


class Base(object):
    def get_choices(self, partial_text):
        raise NotImplementedError

    def get_display_text(self, data):
        raise NotImplementedError


class Model(Base):
    def __init__(self, model=None, field=None, query=None, limit=None):
        if model is None and field is not None and hasattr(field, 'class_'):
            model = field.class_
        if not query:
            if model is None:
                raise Exception('No query provided and could not derive on as '
                                'the model was missing.')
            query = wx.GetApp().session.query(model)
        self.field = field
        self.query = query
        self.limit = limit

    def get_choices(self, partial_text=None):
        if partial_text is not None and len(partial_text) < 2:
            return []
        query = self.query
        if callable(query):
            query = query(partial_text)
        if self.field is not None:
            query = query.filter(self.field.like('%%%s%%' % partial_text))
        if self.limit:
            query = query[0:self.limit]
        return [(data, self.get_display_text(data)) for data in query]

    def get_display_text(self, data):
        return unicode(data or '')
