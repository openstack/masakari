#    Copyright 2016 NTT DATA
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import datetime
import inspect
import os
import pprint
from unittest import mock

from oslo_versionedobjects import exception as ovo_exc
from oslo_versionedobjects import fixture

from masakari import objects
from masakari.objects import base
from masakari.objects import fields
from masakari.objects import segment
from masakari import test
from masakari.tests.unit.objects import fake_args


class MyOwnedObject(base.MasakariPersistentObject, base.MasakariObject):
    VERSION = '1.0'
    fields = {'baz': fields.IntegerField()}


class MyObj(base.MasakariPersistentObject, base.MasakariObject,
            base.MasakariObjectDictCompat):
    VERSION = '1.6'
    fields = {'foo': fields.IntegerField(default=1),
              'bar': fields.StringField(),
              'missing': fields.StringField(),
              'readonly': fields.IntegerField(read_only=True),
              'rel_object': fields.ObjectField('MyOwnedObject', nullable=True),
              'rel_objects': fields.ListOfObjectsField('MyOwnedObject',
                                                       nullable=True),
              'mutable_default': fields.ListOfStringsField(default=[]),
              }

    @staticmethod
    def _from_db_object(context, obj, db_obj):
        self = MyObj()
        self.foo = db_obj['foo']
        self.bar = db_obj['bar']
        self.missing = db_obj['missing']
        self.readonly = 1
        self._context = context
        return self

    def obj_load_attr(self, attrname):
        setattr(self, attrname, 'loaded!')

    @base.remotable_classmethod
    def query(cls, context):
        obj = cls(context=context, foo=1, bar='bar')
        obj.obj_reset_changes()
        return obj

    @base.remotable
    def marco(self):
        return 'polo'

    @base.remotable
    def _update_test(self):
        self.bar = 'updated'

    @base.remotable
    def save(self):
        self.obj_reset_changes()

    @base.remotable
    def refresh(self):
        self.foo = 321
        self.bar = 'refreshed'
        self.obj_reset_changes()

    @base.remotable
    def modify_save_modify(self):
        self.bar = 'meow'
        self.save()
        self.foo = 42
        self.rel_object = MyOwnedObject(baz=42)

    def obj_make_compatible(self, primitive, target_version):
        super(MyObj, self).obj_make_compatible(primitive, target_version)
        if target_version == '1.0' and 'bar' in primitive:
            primitive['bar'] = 'old%s' % primitive['bar']


class TestObjMakeList(test.NoDBTestCase):

    def test_obj_make_list(self):
        class MyList(base.ObjectListBase, base.MasakariObject):
            fields = {
                'objects': fields.ListOfObjectsField('MyObj'),
            }

        db_objs = [{'foo': 1, 'bar': 'baz', 'missing': 'banana'},
                   {'foo': 2, 'bar': 'bat', 'missing': 'apple'},
                   ]
        mylist = base.obj_make_list('ctxt', MyList(), MyObj, db_objs)
        self.assertEqual(2, len(mylist))
        self.assertEqual('ctxt', mylist._context)
        for index, item in enumerate(mylist):
            self.assertEqual(db_objs[index]['foo'], item.foo)
            self.assertEqual(db_objs[index]['bar'], item.bar)
            self.assertEqual(db_objs[index]['missing'], item.missing)


def compare_obj(test, obj, db_obj, subs=None, allow_missing=None,
                comparators=None):
    """Compare a MasakariObject and a dict-like database object.

    This automatically converts TZ-aware datetimes and iterates over
    the fields of the object.

    :param:test: The TestCase doing the comparison
    :param:obj: The MasakariObject to examine
    :param:db_obj: The dict-like database object to use as reference
    :param:subs: A dict of objkey=dbkey field substitutions
    :param:allow_missing: A list of fields that may not be in db_obj
    :param:comparators: Map of comparator functions to use for certain fields
    """

    if subs is None:
        subs = {}
    if allow_missing is None:
        allow_missing = []
    if comparators is None:
        comparators = {}

    for key in obj.fields:
        if key in allow_missing and not obj.obj_attr_is_set(key):
            continue
        obj_val = getattr(obj, key)
        db_key = subs.get(key, key)
        db_val = db_obj[db_key]
        if isinstance(obj_val, datetime.datetime):
            obj_val = obj_val.replace(tzinfo=None)

        if key in comparators:
            comparator = comparators[key]
            comparator(db_val, obj_val)
        else:
            test.assertEqual(db_val, obj_val)


class _BaseTestCase(test.TestCase):
    def setUp(self):
        super(_BaseTestCase, self).setUp()
        self.user_id = 'fake-user'
        self.project_id = 'fake-project'
        self.context = 'masakari-context'

        base.MasakariObjectRegistry.register(MyObj)
        base.MasakariObjectRegistry.register(MyOwnedObject)

    def compare_obj(self, obj, db_obj, subs=None, allow_missing=None,
                    comparators=None):
        compare_obj(self, obj, db_obj, subs=subs, allow_missing=allow_missing,
                    comparators=comparators)

    def str_comparator(self, expected, obj_val):
        """Compare an object field to a string in the db by performing
        a simple coercion on the object field value.
        """
        self.assertEqual(expected, str(obj_val))


class _LocalTest(_BaseTestCase):
    def setUp(self):
        super(_LocalTest, self).setUp()


class _TestObject(object):
    def test_object_attrs_in_init(self):
        # Now check the test one in this file. Should be newest version
        self.assertEqual('1.6', objects.MyObj.VERSION)

    def test_hydration_type_error(self):
        primitive = {'masakari_object.name': 'MyObj',
                     'masakari_object.namespace': 'masakari',
                     'masakari_object.version': '1.5',
                     'masakari_object.data': {'foo': 'a'}}
        self.assertRaises(ValueError, MyObj.obj_from_primitive, primitive)

    def test_hydration(self):
        primitive = {'masakari_object.name': 'MyObj',
                     'masakari_object.namespace': 'masakari',
                     'masakari_object.version': '1.5',
                     'masakari_object.data': {'foo': 1}}
        real_method = MyObj._obj_from_primitive

        def _obj_from_primitive(*args):
            return real_method(*args)

        with mock.patch.object(MyObj, '_obj_from_primitive') as ofp:
            ofp.side_effect = _obj_from_primitive
            obj = MyObj.obj_from_primitive(primitive)
            ofp.assert_called_once_with(None, '1.5', primitive)
        self.assertEqual(obj.foo, 1)

    def test_hydration_version_different(self):
        primitive = {'masakari_object.name': 'MyObj',
                     'masakari_object.namespace': 'masakari',
                     'masakari_object.version': '1.2',
                     'masakari_object.data': {'foo': 1}}
        obj = MyObj.obj_from_primitive(primitive)
        self.assertEqual(obj.foo, 1)
        self.assertEqual('1.2', obj.VERSION)

    def test_hydration_bad_ns(self):
        primitive = {'masakari_object.name': 'MyObj',
                     'masakari_object.namespace': 'foo',
                     'masakari_object.version': '1.5',
                     'masakari_object.data': {'foo': 1}}
        self.assertRaises(ovo_exc.UnsupportedObjectError,
                          MyObj.obj_from_primitive, primitive)

    def test_hydration_additional_unexpected_stuff(self):
        primitive = {'masakari_object.name': 'MyObj',
                     'masakari_object.namespace': 'masakari',
                     'masakari_object.version': '1.5.1',
                     'masakari_object.data': {
                         'foo': 1,
                         'unexpected_thing': 'foobar'}}
        obj = MyObj.obj_from_primitive(primitive)
        self.assertEqual(1, obj.foo)
        self.assertFalse(hasattr(obj, 'unexpected_thing'))
        self.assertEqual('1.5.1', obj.VERSION)

    def test_dehydration(self):
        expected = {'masakari_object.name': 'MyObj',
                    'masakari_object.namespace': 'masakari',
                    'masakari_object.version': '1.6',
                    'masakari_object.data': {'foo': 1}}
        obj = MyObj(foo=1)
        obj.obj_reset_changes()
        self.assertEqual(obj.obj_to_primitive(), expected)

    def test_object_property(self):
        obj = MyObj(foo=1)
        self.assertEqual(obj.foo, 1)

    def test_object_property_type_error(self):
        obj = MyObj()

        def fail():
            obj.foo = 'a'
        self.assertRaises(ValueError, fail)

    def test_load(self):
        obj = MyObj()
        self.assertEqual(obj.bar, 'loaded!')

    def test_load_in_base(self):
        @base.MasakariObjectRegistry.register_if(False)
        class Foo(base.MasakariObject):
            fields = {'foobar': fields.IntegerField()}
        obj = Foo()
        with self.assertRaisesRegex(NotImplementedError, ".*foobar.*"):
            obj.foobar

    def test_loaded_in_primitive(self):
        obj = MyObj(foo=1)
        obj.obj_reset_changes()
        self.assertEqual(obj.bar, 'loaded!')
        expected = {'masakari_object.name': 'MyObj',
                    'masakari_object.namespace': 'masakari',
                    'masakari_object.version': '1.6',
                    'masakari_object.changes': ['bar'],
                    'masakari_object.data': {'foo': 1,
                                         'bar': 'loaded!'}}
        self.assertEqual(obj.obj_to_primitive(), expected)

    def test_changes_in_primitive(self):
        obj = MyObj(foo=123)
        self.assertEqual(obj.obj_what_changed(), set(['foo']))
        primitive = obj.obj_to_primitive()
        self.assertIn('masakari_object.changes', primitive)
        obj2 = MyObj.obj_from_primitive(primitive)
        self.assertEqual(obj2.obj_what_changed(), set(['foo']))
        obj2.obj_reset_changes()
        self.assertEqual(obj2.obj_what_changed(), set())

    def test_orphaned_object(self):
        obj = MyObj.query(self.context)
        obj._context = None
        self.assertRaises(ovo_exc.OrphanedObjectError,
                          obj._update_test)

    def test_changed_1(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(obj.obj_what_changed(), set(['foo']))
        obj._update_test()
        self.assertEqual(obj.obj_what_changed(), set(['foo', 'bar']))
        self.assertEqual(obj.foo, 123)

    def test_changed_2(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(obj.obj_what_changed(), set(['foo']))
        obj.save()
        self.assertEqual(obj.obj_what_changed(), set([]))
        self.assertEqual(obj.foo, 123)

    def test_changed_3(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(obj.obj_what_changed(), set(['foo']))
        obj.refresh()
        self.assertEqual(obj.obj_what_changed(), set([]))
        self.assertEqual(obj.foo, 321)
        self.assertEqual(obj.bar, 'refreshed')

    def test_changed_4(self):
        obj = MyObj.query(self.context)
        obj.bar = 'something'
        self.assertEqual(obj.obj_what_changed(), set(['bar']))
        obj.modify_save_modify()
        self.assertEqual(obj.obj_what_changed(), set(['foo', 'rel_object']))
        self.assertEqual(obj.foo, 42)
        self.assertEqual(obj.bar, 'meow')
        self.assertIsInstance(obj.rel_object, MyOwnedObject)

    def test_changed_with_sub_object(self):
        @base.MasakariObjectRegistry.register_if(False)
        class ParentObject(base.MasakariObject):
            fields = {'foo': fields.IntegerField(),
                      'bar': fields.ObjectField('MyObj'),
                      }
        obj = ParentObject()
        self.assertEqual(set(), obj.obj_what_changed())
        obj.foo = 1
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        bar = MyObj()
        obj.bar = bar
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())
        obj.obj_reset_changes()
        self.assertEqual(set(), obj.obj_what_changed())
        bar.foo = 1
        self.assertEqual(set(['bar']), obj.obj_what_changed())

    def test_static_result(self):
        obj = MyObj.query(self.context)
        self.assertEqual(obj.bar, 'bar')
        result = obj.marco()
        self.assertEqual(result, 'polo')

    def test_updates(self):
        obj = MyObj.query(self.context)
        self.assertEqual(obj.foo, 1)
        obj._update_test()
        self.assertEqual(obj.bar, 'updated')

    def test_contains(self):
        obj = MyObj()
        self.assertNotIn('foo', obj)
        obj.foo = 1
        self.assertIn('foo', obj)
        self.assertNotIn('does_not_exist', obj)

    def test_obj_attr_is_set(self):
        obj = MyObj(foo=1)
        self.assertTrue(obj.obj_attr_is_set('foo'))
        self.assertFalse(obj.obj_attr_is_set('bar'))
        self.assertRaises(AttributeError, obj.obj_attr_is_set, 'bang')

    def test_obj_reset_changes_recursive(self):
        obj = MyObj(rel_object=MyOwnedObject(baz=123),
                    rel_objects=[MyOwnedObject(baz=456)])
        self.assertEqual(set(['rel_object', 'rel_objects']),
                         obj.obj_what_changed())
        obj.obj_reset_changes()
        self.assertEqual(set(['rel_object']), obj.obj_what_changed())
        self.assertEqual(set(['baz']), obj.rel_object.obj_what_changed())
        self.assertEqual(set(['baz']), obj.rel_objects[0].obj_what_changed())
        obj.obj_reset_changes(recursive=True, fields=['foo'])
        self.assertEqual(set(['rel_object']), obj.obj_what_changed())
        self.assertEqual(set(['baz']), obj.rel_object.obj_what_changed())
        self.assertEqual(set(['baz']), obj.rel_objects[0].obj_what_changed())
        obj.obj_reset_changes(recursive=True)
        self.assertEqual(set([]), obj.rel_object.obj_what_changed())
        self.assertEqual(set([]), obj.obj_what_changed())

    def test_get(self):
        obj = MyObj(foo=1)
        # Foo has value, should not get the default
        self.assertEqual(obj.get('foo', 2), 1)
        # Foo has value, should return the value without error
        self.assertEqual(obj.get('foo'), 1)
        # Bar is not loaded, so we should get the default
        self.assertEqual(obj.get('bar', 'not-loaded'), 'not-loaded')
        # Bar without a default should lazy-load
        self.assertEqual(obj.get('bar'), 'loaded!')
        # Bar now has a default, but loaded value should be returned
        self.assertEqual(obj.get('bar', 'not-loaded'), 'loaded!')
        # Invalid attribute should raise AttributeError
        self.assertRaises(AttributeError, obj.get, 'nothing')
        # ...even with a default
        self.assertRaises(AttributeError, obj.get, 'nothing', 3)

    def test_get_changes(self):
        obj = MyObj()
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_obj_fields(self):
        @base.MasakariObjectRegistry.register_if(False)
        class TestObj(base.MasakariObject):
            fields = {'foo': fields.IntegerField()}
            obj_extra_fields = ['bar']

            @property
            def bar(self):
                return 'this is bar'

        obj = TestObj()
        self.assertEqual(['foo', 'bar'], obj.obj_fields)

    def test_obj_constructor(self):
        obj = MyObj(context=self.context, foo=123, bar='abc')
        self.assertEqual(123, obj.foo)
        self.assertEqual('abc', obj.bar)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())

    def test_obj_read_only(self):
        obj = MyObj(context=self.context, foo=123, bar='abc')
        obj.readonly = 1
        self.assertRaises(ovo_exc.ReadOnlyFieldError, setattr,
                          obj, 'readonly', 2)

    def test_obj_mutable_default(self):
        obj = MyObj(context=self.context, foo=123, bar='abc')
        obj.mutable_default = None
        obj.mutable_default.append('s1')
        self.assertEqual(obj.mutable_default, ['s1'])

        obj1 = MyObj(context=self.context, foo=123, bar='abc')
        obj1.mutable_default = None
        obj1.mutable_default.append('s2')
        self.assertEqual(obj1.mutable_default, ['s2'])

    def test_obj_mutable_default_set_default(self):
        obj1 = MyObj(context=self.context, foo=123, bar='abc')
        obj1.obj_set_defaults('mutable_default')
        self.assertEqual(obj1.mutable_default, [])
        obj1.mutable_default.append('s1')
        self.assertEqual(obj1.mutable_default, ['s1'])

        obj2 = MyObj(context=self.context, foo=123, bar='abc')
        obj2.obj_set_defaults('mutable_default')
        self.assertEqual(obj2.mutable_default, [])
        obj2.mutable_default.append('s2')
        self.assertEqual(obj2.mutable_default, ['s2'])

    def test_obj_repr(self):
        obj = MyObj(foo=123)
        self.assertEqual('MyObj(bar=<?>,created_at=<?>,deleted=<?>,'
                         'deleted_at=<?>,foo=123,missing=<?>,'
                         'mutable_default=<?>,readonly=<?>,rel_object=<?>,'
                         'rel_objects=<?>,updated_at=<?>)',
                         repr(obj))

    def test_obj_make_obj_compatible(self):
        subobj = MyOwnedObject(baz=1)
        subobj.VERSION = '1.2'
        obj = MyObj(rel_object=subobj)
        obj.obj_relationships = {
            'rel_object': [('1.5', '1.1'), ('1.7', '1.2')],
        }
        orig_primitive = obj.obj_to_primitive()['masakari_object.data']
        with mock.patch.object(subobj, 'obj_make_compatible') as mock_compat:
            primitive = copy.deepcopy(orig_primitive)
            obj._obj_make_obj_compatible(primitive, '1.8', 'rel_object')
            self.assertFalse(mock_compat.called)

        with mock.patch.object(subobj, 'obj_make_compatible') as mock_compat:
            primitive = copy.deepcopy(orig_primitive)
            obj._obj_make_obj_compatible(primitive, '1.7', 'rel_object')
            mock_compat.assert_called_once_with(
                primitive['rel_object']['masakari_object.data'], '1.2')

        with mock.patch.object(subobj, 'obj_make_compatible') as mock_compat:
            primitive = copy.deepcopy(orig_primitive)
            obj._obj_make_obj_compatible(primitive, '1.6', 'rel_object')
            mock_compat.assert_called_once_with(
                primitive['rel_object']['masakari_object.data'], '1.1')
            self.assertEqual('1.1', primitive[
                'rel_object']['masakari_object.version'])

        with mock.patch.object(subobj, 'obj_make_compatible') as mock_compat:
            primitive = copy.deepcopy(orig_primitive)
            obj._obj_make_obj_compatible(primitive, '1.5', 'rel_object')
            mock_compat.assert_called_once_with(
                primitive['rel_object']['masakari_object.data'], '1.1')
            self.assertEqual('1.1', primitive[
                'rel_object']['masakari_object.version'])

        with mock.patch.object(subobj, 'obj_make_compatible') as mock_compat:
            primitive = copy.deepcopy(orig_primitive)
            obj._obj_make_obj_compatible(primitive, '1.4', 'rel_object')
            self.assertFalse(mock_compat.called)
            self.assertNotIn('rel_object', primitive)

    def test_obj_make_compatible_hits_sub_objects(self):
        subobj = MyOwnedObject(baz=1)
        obj = MyObj(foo=123, rel_object=subobj)
        obj.obj_relationships = {'rel_object': [('1.0', '1.0')]}
        with mock.patch.object(obj, '_obj_make_obj_compatible') as mock_compat:
            obj.obj_make_compatible({'rel_object': 'foo'}, '1.10')
            mock_compat.assert_called_once_with({'rel_object': 'foo'}, '1.10',
                                                'rel_object')

    def test_obj_make_compatible_skips_unset_sub_objects(self):
        obj = MyObj(foo=123)
        obj.obj_relationships = {'rel_object': [('1.0', '1.0')]}
        with mock.patch.object(obj, '_obj_make_obj_compatible') as mock_compat:
            obj.obj_make_compatible({'rel_object': 'foo'}, '1.10')
            self.assertFalse(mock_compat.called)

    def test_obj_make_compatible_doesnt_skip_falsey_sub_objects(self):
        @base.MasakariObjectRegistry.register_if(False)
        class MyList(base.ObjectListBase, base.MasakariObject):
            VERSION = '1.2'
            fields = {'objects': fields.ListOfObjectsField('MyObjElement')}
            obj_relationships = {
                'objects': [('1.1', '1.1'), ('1.2', '1.2')],
            }

        mylist = MyList(objects=[])

        @base.MasakariObjectRegistry.register_if(False)
        class MyOwner(base.MasakariObject):
            VERSION = '1.2'
            fields = {'mylist': fields.ObjectField('MyList')}
            obj_relationships = {
                'mylist': [('1.1', '1.1')],
            }

        myowner = MyOwner(mylist=mylist)
        primitive = myowner.obj_to_primitive('1.1')
        self.assertIn('mylist', primitive['masakari_object.data'])

    def test_obj_make_compatible_handles_list_of_objects(self):
        subobj = MyOwnedObject(baz=1)
        obj = MyObj(rel_objects=[subobj])
        obj.obj_relationships = {'rel_objects': [('1.0', '1.123')]}

        def fake_make_compat(primitive, version):
            self.assertEqual('1.123', version)
            self.assertIn('baz', primitive)

        with mock.patch.object(subobj, 'obj_make_compatible') as mock_mc:
            mock_mc.side_effect = fake_make_compat
            obj.obj_to_primitive('1.0')
            self.assertTrue(mock_mc.called)

    def test_delattr(self):
        obj = MyObj(bar='foo')
        del obj.bar

        # Should appear unset now
        self.assertFalse(obj.obj_attr_is_set('bar'))

        # Make sure post-delete, references trigger lazy loads
        self.assertEqual('loaded!', getattr(obj, 'bar'))

    def test_delattr_unset(self):
        obj = MyObj()
        self.assertRaises(AttributeError, delattr, obj, 'bar')


class TestObject(_LocalTest, _TestObject):
    def test_set_defaults(self):
        obj = MyObj()
        obj.obj_set_defaults('foo')
        self.assertTrue(obj.obj_attr_is_set('foo'))
        self.assertEqual(1, obj.foo)

    def test_set_defaults_no_default(self):
        obj = MyObj()
        self.assertRaises(ovo_exc.ObjectActionError,
                          obj.obj_set_defaults, 'bar')

    def test_set_all_defaults(self):
        obj = MyObj()
        obj.obj_set_defaults()
        self.assertEqual(set(['deleted', 'foo', 'mutable_default']),
                         obj.obj_what_changed())
        self.assertEqual(1, obj.foo)

    def test_set_defaults_not_overwrite(self):
        obj = MyObj(deleted=True)
        obj.obj_set_defaults()
        self.assertEqual(1, obj.foo)
        self.assertTrue(obj.deleted)


class TestRegistry(test.NoDBTestCase):
    @mock.patch('masakari.objects.base.objects')
    def test_hook_chooses_newer_properly(self, mock_objects):
        reg = base.MasakariObjectRegistry()
        reg.registration_hook(MyObj, 0)

        class MyNewerObj(object):
            VERSION = '1.123'

            @classmethod
            def obj_name(cls):
                return 'MyObj'

        self.assertEqual(MyObj, mock_objects.MyObj)
        reg.registration_hook(MyNewerObj, 0)
        self.assertEqual(MyNewerObj, mock_objects.MyObj)

    @mock.patch('masakari.objects.base.objects')
    def test_hook_keeps_newer_properly(self, mock_objects):
        reg = base.MasakariObjectRegistry()
        reg.registration_hook(MyObj, 0)

        class MyOlderObj(object):
            VERSION = '1.1'

            @classmethod
            def obj_name(cls):
                return 'MyObj'

        self.assertEqual(MyObj, mock_objects.MyObj)
        reg.registration_hook(MyOlderObj, 0)
        self.assertEqual(MyObj, mock_objects.MyObj)


# NOTE(Dinesh_Bhor): The hashes in this list should only be changed if
# they come with a corresponding version bump in the affected
# objects
object_data = {
    'FailoverSegment': '1.1-9cecc07c111f647b32d560f19f1f5db9',
    'FailoverSegmentList': '1.0-dfc5c6f5704d24dcaa37b0bbb03cbe60',
    'Host': '1.2-f05735b156b687bc916d46b551bc45e3',
    'HostList': '1.0-25ebe1b17fbd9f114fae8b6a10d198c0',
    'Notification': '1.1-91e3a051078e35300e325a3e2ae5fde5',
    'NotificationProgressDetails': '1.0-fc611ac932b719fbc154dbe34bb8edee',
    'NotificationList': '1.0-25ebe1b17fbd9f114fae8b6a10d198c0',
    'EventType': '1.0-d1d2010a7391fa109f0868d964152607',
    'ExceptionNotification': '1.0-1187e93f564c5cca692db76a66cda2a6',
    'ExceptionPayload': '1.0-96f178a12691e3ef0d8e3188fc481b90',
    'HostApiNotification': '1.0-1187e93f564c5cca692db76a66cda2a6',
    'HostApiPayload': '1.0-20603e23a06477975b860459ba684d34',
    'HostApiPayloadBase': '1.1-e02e80de08d0b584ee7a0a0320bfd029',
    'NotificationApiPayload': '1.0-c050869a1f4aed23e7645bd4d1830ecd',
    'NotificationApiPayloadBase': '1.0-cda8d53a77e64f83e3782fc9c4d499bb',
    'NotificationApiNotification': '1.0-1187e93f564c5cca692db76a66cda2a6',
    'NotificationPublisher': '1.0-bbbc1402fb0e443a3eb227cc52b61545',
    'MyObj': '1.6-ee7b607402fbfb3390a92ab7199e0d88',
    'MyOwnedObject': '1.0-fec853730bd02d54cc32771dd67f08a0',
    'SegmentApiNotification': '1.0-1187e93f564c5cca692db76a66cda2a6',
    'SegmentApiPayload': '1.1-e34e1c772e16e9ad492067ee98607b1d',
    'SegmentApiPayloadBase': '1.1-6a1db76f3e825f92196fc1a11508d886'
}


def get_masakari_objects():
    """Get masakari versioned objects

    This returns a dict of versioned objects which are
    in the Masakari project namespace only. ie excludes
    objects from os-vif and other 3rd party modules

    :return: a dict mapping class names to lists of versioned objects
    """

    all_classes = base.MasakariObjectRegistry.obj_classes()
    masakari_classes = {}
    for name in all_classes:
        objclasses = all_classes[name]
        if (objclasses[0].OBJ_PROJECT_NAMESPACE != (
                base.MasakariObject.OBJ_PROJECT_NAMESPACE)):
            continue
        masakari_classes[name] = objclasses
    return masakari_classes


class TestObjectVersions(test.NoDBTestCase, _BaseTestCase):
    def setUp(self):
        super(test.NoDBTestCase, self).setUp()
        base.MasakariObjectRegistry.register_notification_objects()

    def test_versions(self):
        checker = fixture.ObjectVersionChecker(
            get_masakari_objects())
        fingerprints = checker.get_hashes()

        if os.getenv('GENERATE_HASHES'):
            open('object_hashes.txt', 'w').write(
                pprint.pformat(fingerprints))
            raise test.TestingException(
                'Generated hashes in object_hashes.txt')

        expected, actual = checker.test_hashes(object_data)
        self.assertEqual(expected, actual,
                         'Some objects have changed; please make sure the '
                         'versions have been bumped, and then update their '
                         'hashes here.')

    def test_obj_make_compatible(self):
        base.MasakariObjectRegistry.register(segment.FailoverSegment)

        # Iterate all object classes and verify that we can run
        # obj_make_compatible with every older version than current.
        # This doesn't actually test the data conversions, but it at least
        # makes sure the method doesn't blow up on something basic like
        # expecting the wrong version format.

        # Hold a dictionary of args/kwargs that need to get passed into
        # __init__() for specific classes. The key in the dictionary is
        # the obj_class that needs the init args/kwargs.
        init_args = fake_args.init_args
        init_kwargs = fake_args.init_kwargs

        checker = fixture.ObjectVersionChecker(
            base.MasakariObjectRegistry.obj_classes())
        checker.test_compatibility_routines(use_manifest=True,
                                            init_args=init_args,
                                            init_kwargs=init_kwargs)

    def test_list_obj_make_compatible(self):
        @base.MasakariObjectRegistry.register_if(False)
        class TestObj(base.MasakariObject):
            VERSION = '1.4'
            fields = {'foo': fields.IntegerField()}

        @base.MasakariObjectRegistry.register_if(False)
        class TestListObj(base.ObjectListBase, base.MasakariObject):
            VERSION = '1.5'
            fields = {'objects': fields.ListOfObjectsField('TestObj')}
            obj_relationships = {
                'objects': [('1.0', '1.1'), ('1.1', '1.2'),
                            ('1.3', '1.3'), ('1.5', '1.4')]
            }

        my_list = TestListObj()
        my_obj = TestObj(foo=1)
        my_list.objects = [my_obj]
        primitive = my_list.obj_to_primitive(target_version='1.5')
        primitive_data = primitive['masakari_object.data']
        obj_primitive = my_obj.obj_to_primitive(target_version='1.4')
        obj_primitive_data = obj_primitive['masakari_object.data']
        with mock.patch.object(TestObj, 'obj_make_compatible') as comp:
            my_list.obj_make_compatible(primitive_data, '1.1')
            comp.assert_called_with(obj_primitive_data,
                                    '1.2')

    def test_list_obj_make_compatible_when_no_objects(self):
        # Test to make sure obj_make_compatible works with no 'objects'
        # If a List object ever has a version that did not contain the
        # 'objects' key, we need to make sure converting back to that version
        # doesn't cause backporting problems.
        @base.MasakariObjectRegistry.register_if(False)
        class TestObj(base.MasakariObject):
            VERSION = '1.1'
            fields = {'foo': fields.IntegerField()}

        @base.MasakariObjectRegistry.register_if(False)
        class TestListObj(base.ObjectListBase, base.MasakariObject):
            VERSION = '1.1'
            fields = {'objects': fields.ListOfObjectsField('TestObj')}
            obj_relationships = {
                'objects': [('1.1', '1.1')]
            }

        my_list = TestListObj()
        my_list.objects = [TestObj(foo=1)]
        primitive = my_list.obj_to_primitive(target_version='1.1')
        primitive_data = primitive['masakari_object.data']
        my_list.obj_make_compatible(primitive_data,
                                    target_version='1.0')
        self.assertNotIn('objects', primitive_data,
                         "List was backported to before 'objects' existed."
                         " 'objects' should not be in the primitive.")


class TestObjEqualPrims(_BaseTestCase):

    def test_object_equal(self):
        obj1 = MyObj(foo=1, bar='goodbye')
        obj1.obj_reset_changes()
        obj2 = MyObj(foo=1, bar='goodbye')
        obj2.obj_reset_changes()
        obj2.bar = 'goodbye'
        # obj2 will be marked with field 'three' updated
        self.assertTrue(base.obj_equal_prims(obj1, obj2),
                        "Objects that differ only because one a is marked "
                        "as updated should be equal")

    def test_object_not_equal(self):
        obj1 = MyObj(foo=1, bar='goodbye')
        obj1.obj_reset_changes()
        obj2 = MyObj(foo=1, bar='hello')
        obj2.obj_reset_changes()
        self.assertFalse(base.obj_equal_prims(obj1, obj2),
                         "Objects that differ in any field "
                         "should not be equal")

    def test_object_ignore_equal(self):
        obj1 = MyObj(foo=1, bar='goodbye')
        obj1.obj_reset_changes()
        obj2 = MyObj(foo=1, bar='hello')
        obj2.obj_reset_changes()
        self.assertTrue(base.obj_equal_prims(obj1, obj2, ['bar']),
                        "Objects that only differ in an ignored field "
                        "should be equal")


class TestObjMethodOverrides(test.NoDBTestCase):
    def test_obj_reset_changes(self):
        args = inspect.getfullargspec(base.MasakariObject.obj_reset_changes)
        obj_classes = base.MasakariObjectRegistry.obj_classes()
        for obj_name in obj_classes:
            obj_class = obj_classes[obj_name][0]
            self.assertEqual(args,
                    inspect.getfullargspec(obj_class.obj_reset_changes))
