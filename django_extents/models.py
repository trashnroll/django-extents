import types

from django.db import models
from django.db.models.fields import Field
from django.db.models import Q
from django.db.models.expressions import F, ExpressionNode
from django.db.models.query import QuerySet, ValuesQuerySet, ValuesListQuerySet
from django.utils.encoding import smart_str, force_unicode


class Mapping(dict):
    """
    Mapping is a simple dict subclass for patching the other dicts
    (mostly **kwargs) keys/values according to self contents
    """

    @staticmethod
    def map_dict(d, f_key=None, f_val=None):
        def as_is(x):
            return x
        f_key = f_key or as_is
        f_val = f_val or as_is
        return dict(zip(map(f_key, d.iterkeys()), map(f_val, d.itervalues())))

    def of(self, k):
        """
        Returns mapping of k, or k itself, if corresponding mapping does not
        exist
        """
        return self.get(k, k)

    def map_keys(self, d):
        return Mapping.map_dict(d, f_key=self.of)

    def map_values(self, d):
        return Mapping.map_dict(d, f_val=self.of)

    def mirror(self):
        return Mapping(zip(self.itervalues(), self.iterkeys()))


class QuerySetWrapper(object):
    """
    QuerySetWrapper wraps extent's querysets to patch field names in the queries
    """

    def __init__(self, qs, ExtentClass):
        self._qs = qs
        self._Extent = ExtentClass
        super(QuerySetWrapper, self).__init__()

    def _patch_expr(self, e):
        """
        This function recursively patches django queryset expressions (like Q
        or F), replacing fields occurrences with their mappings
        """
        mapping = self._Extent._meta.proxies

        if isinstance(e, F):
            e.name = mapping.of(e.name)
            return e
        elif isinstance(e, (Q, ExpressionNode)):
            e.children = map(self._patch_expr, e.children)
            return e
        elif isinstance(e, tuple):
            return map(self._patch_expr, e)
        elif isinstance(e, str):
            return mapping.of(e)
        else:
            return e

    def __getattr__(self, name):

        mapping = self._Extent._meta.proxies
        attr = getattr(self._qs, name)

        def qsproxy(*args, **kwargs):

            p_kwargs = Mapping.map_dict(kwargs, mapping.of, self._patch_expr)
            p_args = map(self._patch_expr, args)

            smth = attr(*p_args, **p_kwargs)

            if isinstance(smth, ValuesListQuerySet): # subtype of ValuesQuerySet
                return smth
            elif isinstance(smth, ValuesQuerySet): # subtype of QuerySet
                return map(mapping.mirror().map_keys, smth)
            elif isinstance(smth, QuerySet): # common case
                return QuerySetWrapper(smth, self._Extent)
            elif isinstance(smth, self._Extent._meta.model):
                return self._Extent(smth)
            else:
                return smth

        if isinstance(attr, (models.base.ModelBase, Extent)):
            return attr
        elif callable(attr):
            return qsproxy
        else:
            return attr

    def __iter__(self):
        return (self._Extent(i) for i in self._qs.__iter__())

    def iterator(self):
        for smth in self._qs.iterator():
            if isinstance(smth, QuerySet):
                yield QuerySetWrapper(smth, self._Extent)
            elif isinstance(smth, self._Extent._meta.model):
                yield self._Extent(smth)
            else:
                yield smth

    def __len__(self):
        return self._qs.__len__()

    def __getitem__(self, k):
        item = self._qs.__getitem__(k)
        if isinstance(item, QuerySet):
            return QuerySetWrapper(item, self._Extent)
        else:
            return self._Extent(item)

    def __repr__(self):
        from django.db.models.query import REPR_OUTPUT_SIZE
        data = list(map(self._Extent, self._qs[:REPR_OUTPUT_SIZE + 1]))
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)


class ExtentConstructor(models.base.ModelBase):
    """
    A metaclass for Extents subclasses construction
    """

    def __new__(cls, name, bases, attrs):
        # we don't need anything to be inherited from ModelBase
        return type.__new__(cls, name, bases, attrs)

    def wrap(cls, attrname):

        attr = getattr(cls, attrname)
        inject_name = '%s_%s' % (cls._meta.real_app_label, attrname)

        if callable(attr):
            def proxy(s, *args, **kwargs):
                return attr(cls(s), *args, **kwargs)
            cls._meta.model.add_to_class(inject_name, proxy)

        elif isinstance(attr, Field):
            cls._meta.model.add_to_class(inject_name, attr)
            delattr(cls, attrname)
            cls._meta.proxies[attrname] = inject_name

        elif isinstance(attr, models.Manager):
            class ManagerWrapper(models.Manager):
                def get_query_set(self):
                    qs = super(ManagerWrapper, self).get_query_set()
                    return QuerySetWrapper(qs, cls)

            attr.__class__.__bases__ = (ManagerWrapper, )
            attr.model = cls._meta.model
            attr.model._meta.db_table = cls._meta.model._meta.db_table

    def __init__(cls, name, bases, attrs):

        # check this to ensure that class construction works with Extent
        # subclasses but not with Extent class itself
        if '__metaclass__' not in cls.__dict__:

            cls._meta = attrs.pop('Meta', type('Meta', (), {}))

            # app label is usually a part just before ".models"
            cls._meta.real_app_label = attrs['__module__'].split('.')[-2]

            cls._meta.proxies = Mapping()

            if 'objects' not in attrs:
                cls.objects = QuerySetWrapper(cls._meta.model.objects, cls)

            cls._default_manager = cls.objects

            for k in attrs.iterkeys():
                if k != '__module__':
                    cls.wrap(k)

            cls.__realmodule__ = cls.__module__
            cls.__realname__ = cls.__name__

            # this voodoo magic is for registering extent in django admin site
            cls.__module__ = cls._meta.model.__module__
            cls.__name__ = cls._meta.model.__name__

            cls._meta.model.add_to_class('as_%s_%s' % (cls._meta.real_app_label,
                        cls.__realname__), lambda s: cls(s))

            for i in ('app_label', 'module_name', 'get_add_permission',
                      'get_change_permission', 'get_delete_permission',
                      'verbose_name_plural', 'ordering', 'pk', 'get_field',
                      'verbose_name', 'get_ordered_objects', 'object_name',
                      'get_field_by_name', 'fields', 'many_to_many', 'proxy',
                      'verbose_name_raw'):
                if not hasattr(cls._meta, i):
                    setattr(cls._meta, i, getattr(cls._meta.model._meta, i))

        super(ExtentConstructor, cls).__init__(name, bases, attrs)


class Extent(object):
    """
    Extent is a main and the only package class for external using. It is a base
    class for model extents, and it contains all necessary machinery to be
    used instead of original model class in all (I hope) possible cases.
    """

    __metaclass__ = ExtentConstructor

    def __getattr__(self, name):
        """
        Proxying attribute queries to the actual model instance
        """
        return getattr(self._instance, self._meta.proxies.of(name))

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs and isinstance(args[0], models.Model):
            instance = args[0]
        else:
            mapping = self._meta.proxies
            instance = self._meta.model(*args, **mapping.map_keys(kwargs))
        self.__dict__['_instance'] = instance

    def __setattr__(self, name, value):
        name = self._meta.proxies.of(name)
        if hasattr(self._instance, name):
            setattr(self._instance, name, value)
        else:
            self.__dict__[name] = value

    def __repr__(self):
        """
        copy-pasted from models.Model.__repr__
        """
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        return smart_str(u'<%s: %s>' % (self.__class__.__realname__, u))

    def __str__(self):
        if '__unicode__' in self.__dict__:
            return force_unicode(self).encode('utf-8')
        elif hasattr(self._meta.model, '__unicode__'):
            return force_unicode(self._instance).encode('utf-8')
        return '%s object' % self.__class__.__realname__

