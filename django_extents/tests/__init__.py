import unittest

from django.db.models import F, Q
from django.contrib.auth.models import User

from django.core.exceptions import FieldError

from django_extents.tests.models import MyUser

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        u = User.objects.create_user('user', 'user@example.com', 'password')
        u.tests_tags = 'tag1 tag2'
        u.save()

    def tearDown(self):
        User.objects.all().delete()


class MainTestCase(BasicTestCase):

    def test_instantiation(self):
        n = MyUser()
        self.assertEquals(n.tags, '')

    def test_cast(self):
        n = User()
        m = MyUser(n)
        self.assertTrue(isinstance(m, MyUser))

    def test_passing_init_parameters(self):
        m = MyUser(tags='tag1 tag2')
        self.assertEquals(m.tags, 'tag1 tag2')

    def test_passing_parameters(self):
        m = MyUser()
        m.tags = 'tag1 tag2'
        self.assertEquals(m.tags, 'tag1 tag2')

    def test_saving(self):
        m = MyUser(username='user2', email='user@example.com', password='dummy',
                   tags='tag1 tag2')
        m.save()
        self.assertEquals(MyUser.objects.filter(username='user2').count(), 1)

    def test_deleting(self):
        m = MyUser.objects.get(username='user')
        m.delete()
        self.assertEquals(MyUser.objects.filter(username='user').count(), 0)

    def test_setting_and_saving_attributes(self):
        m = MyUser(username='user2', email='user@example.com', password='dummy',
                   tags='tag1 tag2')
        m.save()
        del m
        m = MyUser.objects.get(username='user2')
        self.assertEquals(m.tags, 'tag1 tag2')

class QSTestCase(BasicTestCase):

    def test_qs_count(self):
        self.assertEquals(MyUser.objects.count(), User.objects.count())

    def test_qs_len(self):
        my_users = MyUser.objects.all()
        users = User.objects.all()

        self.assertEquals(len(my_users), my_users.count())
        self.assertEquals(len(users), len(my_users))

    def test_qs_get(self):
        self.assertTrue(MyUser.objects.get(username='user') is not None)

    def test_qs_getitem(self):
        self.assertTrue(MyUser.objects.all()[0] is not None)

    def test_qs_slice(self):
        self.assertTrue(MyUser.objects.all()[:].count())

    def test_qs_F_patching(self):
        self.assertEquals(list(MyUser.objects.all().values_list('pk')),
                  list(MyUser.objects.filter(tags=F('tags')).values_list('pk')))

    def test_qs_Q_patching(self):
        self.assertEquals(
            list(MyUser.objects.filter(Q(tags='tag1 tag2')).values_list('pk')),
            list(MyUser.objects.all().values_list('pk'))
        )

    def test_qs_QF_patching(self):
        self.assertEquals(
            list(MyUser.objects.filter(Q(tags='tag1 tag2')).values_list('pk')),
            list(MyUser.objects.filter(Q(tags='tag1 tag2') | Q(tags=F('tags')))
                 .values_list('pk'))
        )

    def test_qs_update(self):
        MyUser.objects.update(tags='')
        self.assertEquals(MyUser.objects.count(),
                          MyUser.objects.filter(tags='').count())
        MyUser.objects.update(tags='tag1 tag2')
        self.assertEquals(MyUser.objects.count(),
                          MyUser.objects.filter(tags='tag1 tag2').count())

    def test_qs_values(self):
        self.assertEquals(list(MyUser.objects.values('tags')),
                          [{'tags': u'tag1 tag2'}])

    def test_qs_values_list(self):
        my_users = MyUser.objects.all()
        users = User.objects.all()

        self.assertEquals(list(my_users.values_list('pk')),
                          list(users.values_list('pk')))


class ManagersTestCase(BasicTestCase):

    def test_native_manager_attr_proxy(self):
        try:
            MyUser.objects.filter(tags='')
        except FieldError:
            self.fail("Native manager is not wrapped properly")

    def test_extent_manager_attr_proxy(self):
        try:
            MyUser.custom_objects.get_tagged_users()
        except FieldError:
            self.fail("Custom manager is not wrapped properly")

    def test_native_manager_returns_extents(self):
        self.assertTrue(isinstance(MyUser.objects.latest('pk'), MyUser))

    def test_extent_manager_returns_extents(self):
        self.assertTrue(isinstance(MyUser.custom_objects.latest('pk'), MyUser))

