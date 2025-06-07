from django.urls import path
from . import views


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),  # Home page view
    path('classify/', views.ClassifyView.as_view(), name='classify'),  # Classification endpoint
]