
from django.db import models
from django.contrib.auth.models import User

from django_extents.models import Extent


class MyUserManager(models.Manager):

    def get_query_set(self):
        return super(MyUserManager, self).get_query_set().filter(is_active=True)

    def get_tagged_users(self):
        return self.get_query_set().exclude(tags='')


class MyUser(Extent):

    custom_objects = MyUserManager()

    tags = models.CharField(max_length=128)

    class Meta:
        model = User

    def get_tags(self):
        return self.tags.split()

    def __unicode__(self):
        return u'custom user with tags "%s"' % self.tags
