from django.apps import AppConfig
from django.conf import settings


class BooruConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'booru'
    
    
    def ready(self):
        from booru.views import getMetaDataFromHydrusById
        from os import getenv
        
        class psuedo_request:
            def __init__(self):
                pass
            
            session = {
                'key': ''
            }
            
            
        booru_key = getenv("BOORU_KEY")
        req = psuedo_request()
        req.session['key'] = booru_key
        tag_options = getMetaDataFromHydrusById(req, 1)['tags']
        for tag_lib in tag_options:
            if tag_options[tag_lib]['name'] == 'all known tags':
                settings.ALL_KNOWN_TAGS_CODE = tag_lib
                break
        
        

        
        