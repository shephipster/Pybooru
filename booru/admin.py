from django.contrib import admin

from booru.models import Subooru

class SubooruAdmin(admin.ModelAdmin):
    filter_horizontal = ('files', )

# Register your models here.
admin.site.register(Subooru, SubooruAdmin)

