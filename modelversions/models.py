from django.db import models
from django.db.models import F, signals
from django.db import router, transaction
from django.db.models.fields import AutoField
from django.db import DatabaseError

class ConcurrentModificationException(Exception):
    pass

class VersionedModel(models.Model):
    _version = models.IntegerField(null=False, blank=True)

    def save_base_with_version(self,
            raw=False, cls=None, origin=None, force_insert=False, 
            force_update=False, using=None, update_fields=None):

        using = using or router.db_for_write(self.__class__, instance=self)
        assert not (force_insert and (force_update or update_fields))
        assert update_fields is None or len(update_fields) > 0
        if cls is None:
            cls = self.__class__
            meta = cls._meta
            if not meta.proxy:
                origin = cls
        else:
            meta = cls._meta

        if origin and not meta.auto_created:
            signals.pre_save.send(sender=origin, instance=self, raw=raw, using=using,
                                  update_fields=update_fields)

        # If we are in a raw save, save the object exactly as presented.
        # That means that we don't try to be smart about saving attributes
        # that might have come from the parent class - we just save the
        # attributes we have been given to the class we have been given.
        # We also go through this process to defer the save of proxy objects
        # to their actual underlying model.
        if not raw or meta.proxy:
            if meta.proxy:
                org = cls
            else:
                org = None
            for parent, field in meta.parents.items():
                # At this point, parent's primary key field may be unknown
                # (for example, from administration form which doesn't fill
                # this field). If so, fill it.
                if field and getattr(self, parent._meta.pk.attname) is None and getattr(self, field.attname) is not None:
                    setattr(self, parent._meta.pk.attname, getattr(self, field.attname))

                self.save_base(cls=parent, origin=org, using=using,
                               update_fields=update_fields)

                if field:
                    setattr(self, field.attname, self._get_pk_val(parent._meta))
                    # Since we didn't have an instance of the parent handy, we
                    # set attname directly, bypassing the descriptor.
                    # Invalidate the related object cache, in case it's been
                    # accidentally populated. A fresh instance will be
                    # re-built from the database if necessary.
                    cache_name = field.get_cache_name()
                    if hasattr(self, cache_name):
                        delattr(self, cache_name)

            if meta.proxy:
                return

        if not meta.proxy:
            non_pks = [f for f in meta.local_fields if not f.primary_key]

            if update_fields:
                non_pks = [f for f in non_pks if f.name in update_fields or f.attname in update_fields]

            # First, try an UPDATE. If that doesn't update anything, do an INSERT.
            pk_val = self._get_pk_val(meta)
            record_exists = True
            manager = cls._base_manager

            values = []
            for f in non_pks:
                if f.name == '_version':
                    values.append((f, None, F('_version') + 1))
                else:
                    values.append((f, None, (raw and getattr(self, f.attname) or f.pre_save(self, False))))
                            
            if values:
                rows = manager.using(using)\
                        .filter(pk=pk_val, _version=self._version)\
                        ._update(values)

                if not rows:
                    raise ConcurrentModificationException('Model updated already, was version %d' % self._version)
                self._version += 1

                if force_update and not rows:
                    raise DatabaseError("Forced update did not affect any rows.")
                if update_fields and not rows:
                    raise DatabaseError("Save with update_fields did not affect any rows.")
            transaction.commit_unless_managed(using=using)

        # Store the database on which the object was saved
        self._state.db = using
        # Once saved, this is no longer a to-be-added instance.
        self._state.adding = False

        # Signal that the save is complete
        if origin and not meta.auto_created:
            signals.post_save.send(sender=origin, instance=self, created=(not record_exists),
                                   update_fields=update_fields, raw=raw, using=using)

    def save_base(self, raw=False, cls=None, origin=None, force_insert=False, 
                  force_update=False, using=None, update_fields=None):
        '''If this model already exists then this performs an update to ensure
        that the model has not already been updated.'''
        if self._version:
            return self.save_base_with_version(raw, cls, origin, force_insert,
                    force_update, using, update_fields)
        else:
            self._version = 1
            return super(VersionedModel, self).save_base(
                raw=raw, cls=cls, origin=origin, force_insert=force_insert, 
                force_update=force_update, using=using, update_fields=update_fields)
    save_base.alters_data = True

    class Meta:
        abstract = True
