from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name='Personal'),
	path('services/', views.services, name='services'),
]
