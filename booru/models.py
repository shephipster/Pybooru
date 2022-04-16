from django.db import models

# Create your models here.
class Subooru(models.Model):
    key = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
class Tag(models.Model):
    key = models.AutoField(primary_key=True)
    name = models.CharField(max_length = 100)
    count = models.IntegerField()
    
    def __str__(self):
        return self.name

class File(models.Model):
    key = models.AutoField(primary_key=True)
    hash = models.CharField(max_length=256)
    
    def __str__(self):
        return self.hash
    
class Booru_File_Pair(models.Model):
    key = models.AutoField(primary_key=True)
    blacklist = models.BooleanField(default=False)
    booru_key = models.ForeignKey(Subooru, on_delete=models.CASCADE)
    file_key = models.ForeignKey(File, on_delete=models.CASCADE)
    
class Booru_Tag_Pair(models.Model):
    key = models.AutoField(primary_key=True)
    blacklist = models.BooleanField(default=False)
    booru_key = models.ForeignKey(Subooru, on_delete=models.CASCADE)
    tag_key = models.ForeignKey(Tag, on_delete=models.CASCADE)