from django.urls import path
from booru import views

urlpatterns = [
    path("", views.home, name="home"),
    path("auth/", views.authorize, name="auth"),
    path("booru/", views.booru, name="booru"),
    path("booru/search", views.search, name="search")
]