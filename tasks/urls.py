from django.urls import path

from . import views

app_name = 'tasks'

# Included under workspaces/<int:workspace_pk>/projects/<int:project_pk>/tasks/
# (config/urls.py).
urlpatterns = [
    path('new/', views.TaskCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='detail'),
    path('<int:pk>/assign/', views.TaskAssignView.as_view(), name='assign'),
    path('<int:pk>/status/', views.TaskStatusView.as_view(), name='status'),
]
