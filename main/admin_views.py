from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from datetime import datetime
from functools import wraps
from bson import ObjectId
from .db import get_db

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('admin_logged_in'):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_login(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        if password == getattr(settings, 'ADMIN_PASSWORD', 'admin123'):
            request.session['admin_logged_in'] = True
            return redirect('admin_dashboard')
        else:
            return render(request, 'main/admin/login.html', {'error': 'Invalid password'})
    return render(request, 'main/admin/login.html')

def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')

@admin_required
def dashboard(request):
    db = get_db()
    project_count = db.projects.count_documents({})
    blog_count = db.blogs.count_documents({})
    return render(request, 'main/admin/dashboard.html', {
        'project_count': project_count,
        'blog_count': blog_count
    })

@admin_required
def edit_profile(request):
    db = get_db()
    profile = db.profile.find_one() or {}
    
    if request.method == 'POST':
        profile_data = {
            'name': request.POST.get('name'),
            'title': request.POST.get('title'),
            'bio': request.POST.get('bio'),
            'email': request.POST.get('email'),
            'github': request.POST.get('github'),
            'linkedin': request.POST.get('linkedin'),
        }
        if profile.get('_id'):
            db.profile.update_one({'_id': profile['_id']}, {'$set': profile_data})
        else:
            db.profile.insert_one(profile_data)
            
        return redirect('admin_profile')
        
    return render(request, 'main/admin/edit_profile.html', {'profile': profile})

@admin_required
def list_blogs(request):
    db = get_db()
    blogs = list(db.blogs.find().sort('created_at', -1))
    for b in blogs:
        b['id'] = str(b['_id'])
    return render(request, 'main/admin/list_blogs.html', {'blogs': blogs})

@admin_required
def edit_blog(request, blog_id=None):
    db = get_db()
    blog = {}
    if blog_id:
        blog = db.blogs.find_one({'_id': ObjectId(blog_id)})
        blog['id'] = str(blog['_id'])
        
    if request.method == 'POST':
        blog_data = {
            'title': request.POST.get('title'),
            'content': request.POST.get('content'),
            'is_published': request.POST.get('is_published') == 'on',
        }
        if blog_id:
            db.blogs.update_one({'_id': ObjectId(blog_id)}, {'$set': blog_data})
        else:
            blog_data['created_at'] = datetime.now()
            db.blogs.insert_one(blog_data)
            
        return redirect('admin_blogs')
        
    return render(request, 'main/admin/edit_blog.html', {'blog': blog})

@admin_required
def delete_blog(request, blog_id):
    db = get_db()
    if request.method == 'POST':
        db.blogs.delete_one({'_id': ObjectId(blog_id)})
    return redirect('admin_blogs')
