from django.db import models
from django.db.models import F

class ConcurrentModificationException(Exception):
    pass

class VersionedModel(models.Model):
    _version = models.IntegerField()


    def save(self, *args, **kwargs):
        '''If this model already exists then this performs an update to ensure
        that the model has not already been updated.'''
        if self._version:
            updated = self.__class__.objects.filter(id=self.id)\
                                            .update(_version=F('_version') + 1)
            if updated:
                # TODO Signals, pre-save, post-save
                self._version += 1
                return
            else:
                raise ConcurrentModificationException()

        else:
            super(VersionedModel, self).save(*args, **kwargs)


    class Meta:
        abstract = True
