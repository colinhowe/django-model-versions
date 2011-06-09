from django.db import models
from django.db.models import F, signals
from django.db import router, connections

class ConcurrentModificationException(Exception):
    pass

class VersionedModel(models.Model):
    _version = models.IntegerField(null=False, blank=True)


    def save(self, force_insert=False, force_update=False, using=None):
        '''If this model already exists then this performs an update to ensure
        that the model has not already been updated.'''
        if self._version:
            # Pre-save signalling based on Django's way of doing it
            using = using or router.db_for_write(self.__class__, instance=self)
            connection = connections[using]
            assert not (force_insert and force_update)
            cls = self.__class__
            meta = cls._meta
            if not meta.proxy:
                origin = cls

            if origin and not meta.auto_created:
                signals.pre_save.send(sender=origin, instance=self, raw=False, using=using)

            non_pks = [f for f in meta.local_fields if not f.primary_key]
            manager = cls._base_manager
            pk_val = self._get_pk_val(meta)
                                        
            values = []
            for f in non_pks:
                if f.name == '_version':
                    values.append((f, None, F('_version') + 1))
                else:
                    values.append((f, None, f.pre_save(self, False)))
                
            updated = self.__class__.objects.filter(pk=pk_val, _version=self._version)\
                                            ._update(values)
            if updated:
                self._version += 1
                        # Signal that the save is complete
                if origin and not meta.auto_created:
                    signals.post_save.send(sender=origin, instance=self,
                        created=False, raw=False, using=using)
                return
            else:
                raise ConcurrentModificationException('Model updated already, was version %d' % self._version)

        else:
            self._version = 1
            return super(VersionedModel, self).save(
                force_insert=force_insert,
                force_update=force_update,
                using=using)


    class Meta:
        abstract = True
