from django.urls import path
from . import views

urlpatterns = [
    path('asylum-intake/', views.intake_form, name='intake_form'),
    path('intake-success/', views.intake_success, name='intake_success'),
]


