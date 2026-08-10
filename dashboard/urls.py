from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import DashboardLoginForm
from .views import CaseDetailView, CaseQueueView

app_name = 'dashboard'

urlpatterns = [
    path('', CaseQueueView.as_view(), name='queue'),
    path('<int:pk>/', CaseDetailView.as_view(), name='detail'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='dashboard/login.html',
            authentication_form=DashboardLoginForm,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
