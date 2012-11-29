from __future__ import absolute_import
import unittest
import mock
import wx

import traits.api as traits
from traits.trait_notifiers import set_ui_handler

import mvvm.viewbinding.table as subject

set_ui_handler( wx.CallAfter )

class TestListTable(unittest.TestCase):
    class TItem(traits.HasTraits):
        value = traits.Str()

    class TList(traits.HasTraits):
        objects = traits.List(traits.HasTraits)

    def test_items(self):
        trait = self.TList()

        table = subject.ListTable((trait, 'objects'))
        table.UpdateValues = mock.MagicMock()
        table.ResetView = mock.MagicMock()

        trait.objects.append(self.TItem(value='Row 1'))
        self.assert_(table.ResetView.called)
        table.UpdateValues.reset_mock()
        table.ResetView.reset_mock()

        trait.objects.append(self.TItem(value='Row 2'))
        self.assert_(table.ResetView.called)
        table.UpdateValues.reset_mock()
        table.ResetView.reset_mock()

        trait.objects.pop()
        self.assert_(table.ResetView.called)
        table.UpdateValues.reset_mock()
        table.ResetView.reset_mock()

        trait.objects = []
        self.assert_(table.ResetView.called)

    def test_item_value(self):
        trait = self.TList()

        table = subject.ListTable((trait, 'objects'))
        table.UpdateValues = mock.MagicMock()
        table.ResetView = mock.MagicMock()

        row = self.TItem(value='Row 1')

        trait.objects.append(row)
        table.ResetView.reset_mock()
        table.UpdateValues.reset_mock()

        row.value = 'Row 1 - changed'
        self.assert_(table.ResetView.called or table.UpdateValues.called)

if __name__ == '__main__':
    unittest.main()
