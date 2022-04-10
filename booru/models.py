from django.db import models
from django.contrib.postgres.fields import ArrayField

# Create your models here.
class Subooru(models.Model):
    key = models.AutoField(primary_key=True)
    ids = ArrayField(models.IntegerField())
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name