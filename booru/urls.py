from django.urls import path
from booru import views

urlpatterns = [
    path("", views.home, name="home"),
    path("auth/", views.authorize, name="auth"),
    path("booru/", views.booru, name="booru"),
    path("booru/search", views.search, name="search"),
    path("booru/add_to_booru", views.add_to_booru, name="addToBooru"),
    path("booru/add_all_to_subooru", views.add_all_to_subooru, name="addAll"),
    path("booru/create_from_search", views.create_booru_from_results),
    path("thumbnail/<id>", views.thumbnail, name="thumbnail"),
    path("view/<id>", views.view, name="view"),
    path("image/<id>", views.image, name="image"),
    path("view/full/<id>", views.fullImage, name="fullImage"),
    path("create/subooru", views.create_subooru, name="createSubooru"),
    path('update', views.updateTables, name='update'),
    path('embed/<int:id>', views.embedLink, name="embedLink"),
    path('embed/full/<int:id>', views.fullImage, name="embedFull"),
    
]