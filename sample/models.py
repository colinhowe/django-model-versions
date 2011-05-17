from django.db import models
from modelversions import VersionedModel

# Create your models here.
class Comment(VersionedModel):
    text = models.CharField(max_length=255)
