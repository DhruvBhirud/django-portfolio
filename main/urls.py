from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('project/<slug:project_slug>/', views.project_detail, name='project_detail'),
    path('blogs/', views.blog_index, name='blog_index'),
    path('blog/<slug:blog_slug>/', views.blog_detail, name='blog_detail'),
    path('contact/submit/', views.submit_contact, name='submit_contact'),
]