from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import DashboardLoginForm
from .views import CaseDetailView, CaseQueueView, CaseSearchView, CaseStatusUpdateView

app_name = 'dashboard'

urlpatterns = [
    path('', CaseQueueView.as_view(), name='queue'),
    path('search/', CaseSearchView.as_view(), name='search'),
    path('<int:pk>/', CaseDetailView.as_view(), name='detail'),
    path('<int:pk>/status/', CaseStatusUpdateView.as_view(), name='status'),
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
