from django.urls import path

from . import views

app_name = 'projects'

# Included under workspaces/<int:workspace_pk>/projects/ (config/urls.py).
urlpatterns = [
    path('new/', views.ProjectCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
]
