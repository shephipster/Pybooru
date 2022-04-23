# Generated by Django 4.0.3 on 2022-04-22 22:27

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('booru', '0005_alter_subooru_files_alter_subooru_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subooru',
            name='files',
            field=models.ManyToManyField(blank=True, null=True, related_name='files', to='booru.file'),
        ),
        migrations.AlterField(
            model_name='subooru',
            name='key',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
