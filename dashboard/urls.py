from django.contrib.auth import views as auth_views
from django.urls import path

from .views import CaseQueueView

app_name = 'dashboard'

urlpatterns = [
    path('', CaseQueueView.as_view(), name='queue'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='dashboard/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
