from django.urls import path
from . import admin_views

urlpatterns = [
    path('login/', admin_views.admin_login, name='admin_login'),
    path('logout/', admin_views.admin_logout, name='admin_logout'),
    path('', admin_views.dashboard, name='admin_dashboard'),
    path('profile/', admin_views.edit_profile, name='admin_profile'),
    path('blogs/', admin_views.list_blogs, name='admin_blogs'),
    path('blogs/add/', admin_views.edit_blog, name='admin_blog_add'),
    path('blogs/edit/<str:blog_id>/', admin_views.edit_blog, name='admin_blog_edit'),
    path('blogs/delete/<str:blog_id>/', admin_views.delete_blog, name='admin_blog_delete'),
    path('skills/', admin_views.manage_skills, name='admin_skills'),
    path('skills/reorder/', admin_views.reorder_skills, name='admin_skills_reorder'),
    path('skills/edit/<str:skill_id>/', admin_views.edit_skill, name='admin_skill_edit'),
    path('skills/delete/<str:skill_id>/', admin_views.delete_skill, name='admin_skill_delete'),
    path('projects/', admin_views.list_projects, name='admin_projects'),
    path('projects/add/', admin_views.edit_project, name='admin_project_add'),
    path('projects/edit/<str:project_id>/', admin_views.edit_project, name='admin_project_edit'),
    path('projects/delete/<str:project_id>/', admin_views.delete_project, name='admin_project_delete'),
    path('upload-image/', admin_views.upload_image, name='admin_upload_image'),
    path('messages/', admin_views.list_messages, name='admin_messages'),
    path('messages/view/<str:message_id>/', admin_views.view_message, name='admin_view_message'),
    path('messages/delete/<str:message_id>/', admin_views.delete_message, name='admin_delete_message'),
    path('settings/', admin_views.admin_settings, name='admin_settings'),
]
