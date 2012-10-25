from __future__ import absolute_import
import unittest
from traits.has_traits import HasTraits
from traits.traits import CTrait
from model import Skater
from mvvm.viewmodel.wrapper import wrap, wrap_cls

class TestWrap(unittest.TestCase):

    def test(self):
        obj_cls = wrap_cls(Skater)
        self.assertEqual('WrappedSkater', obj_cls.__name__)

        obj = Skater(first_name='Bouke')
        wrapped = wrap(obj, True)
        self.assertIsInstance(wrapped, obj_cls)
        self.assertIsInstance(wrapped, HasTraits)

        self.assertIsInstance(wrapped.trait('first_name'), CTrait)
        self.assertEqual('Bouke', wrapped.first_name)

        wrapped.first_name = 'Arie'
        self.assertEqual('Arie', wrapped.first_name)
        self.assertEqual('Arie', obj.first_name)

        obj2 = Skater(first_name='Bouke')
        wrapped2 = wrap(obj2, False)
        wrapped2.first_name = 'Frida'
        self.assertEqual('Frida', wrapped2.first_name)
        self.assertEqual('Bouke', obj2.first_name)
        self.assertEqual('Arie', wrapped.first_name)
        self.assertEqual({'first_name': 'Frida'}, wrapped2.changes)
        wrapped2.write()
        self.assertEqual('Frida', obj2.first_name)


if __name__ == '__main__':
    unittest.main()
