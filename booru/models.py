import uuid
from django.db import models

# Create your models here.
    
class Tag(models.Model):
    key = models.AutoField(primary_key=True)
    name = models.CharField(max_length = 100)
    count = models.IntegerField()
    
    def __str__(self):
        return self.name

class File(models.Model):
    key = models.AutoField(primary_key=True)
    id = models.IntegerField(null=True)
    hash = models.CharField(max_length=256)
    
    def __str__(self):
        return self.hash
    
class Subooru(models.Model):
    key = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    files = models.ManyToManyField(File, blank=True, null=True, related_name="files")
        
    def __str__(self):
        return self.name