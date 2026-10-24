from django.urls import path

from . import views

app_name = 'workspaces'

urlpatterns = [
    path('new/', views.WorkspaceCreateView.as_view(), name='create'),
    path('<int:pk>/', views.WorkspaceDetailView.as_view(), name='detail'),
    path(
        '<int:pk>/members/add/',
        views.AddMemberView.as_view(),
        name='add_member',
    ),
]
