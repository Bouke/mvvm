from __future__ import absolute_import
import unittest

import mock
from sqlalchemy import event
from traits.has_traits import HasTraits
from traits.traits import CTrait

from common.models import Skater, Country
from mvvm.viewmodel import wrapper
from mvvm.viewmodel.wrapper import wrap, wrap_cls
from tests import engine, Session

class TestWrap(unittest.TestCase):

    def test(self):
        wrapped_cls = wrap_cls(Skater, True)
        self.assertEqual('TransparentWrappedSkater', wrapped_cls.__name__)

        obj = Skater(first_name='Bouke')
        wrapped = wrap(obj, True)
        self.assertEqual(wrapped, obj)
        self.assertIsInstance(wrapped, wrapped_cls)
        self.assertIsInstance(wrapped, HasTraits)

        self.assertIn('first_name', wrapped.traits())
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
        wrapped2.flush()
        self.assertEqual('Frida', obj2.first_name)

        name = 'Bouke'
        calls = []
        def callback(value):
            calls.append(value)
        obj2 = wrap(Skater(first_name=name))
        obj2.on_trait_change(callback, 'first_name')
        obj2.first_name = 'Botje'
        self.assertEqual(1, len(calls), 'Callback was not executed')
        self.assertEqual(calls[0], 'Botje')

    def test_sqlalchemy(self):
        connection = engine.connect()
        trans = connection.begin()
        session = Session(bind=connection)
        event.listen(session, 'after_flush', wrapper.session_flush)

        skater = Skater(
            first_name='Bouke',
            last_name='Haarsma',
            gender='M',
            country=Country(code='NED', name='Netherlands'),
        )
        wrapped_skater = wrap(skater)

        checker = mock.MagicMock()
        def listener(trait, name, old, new):
            checker(trait=trait, name=name, old=old, new=new)
        wrapped_skater.on_trait_change(listener)

        session.add(skater)
        session.commit()
        self.assert_(checker.called)
        checker.reset_mock()

        skater.first_name = 'Botje'
        session.commit()
        self.assert_(checker.called)
        checker.reset_mock()

if __name__ == '__main__':
    unittest.main()
