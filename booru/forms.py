from django.forms import ModelForm
from .models import Subooru

class SubooruForm(ModelForm):
    class Meta:
        model = Subooru
        fields = ['name']