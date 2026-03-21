from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('project/<str:project_id>/', views.project_detail, name='project_detail'),
    path('blogs/', views.blog_index, name='blog_index'),
    path('blog/<str:blog_id>/', views.blog_detail, name='blog_detail'),
]