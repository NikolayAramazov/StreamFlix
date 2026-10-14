# catalog/urls.py
from django.urls import path
from . import views

app_name = "catalog"
urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("title/<slug:slug>/", views.detail, name="detail"),
    path("progress/", views.save_progress, name="progress"),
]