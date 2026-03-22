from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from functools import wraps
from bson import ObjectId
from .db import get_db
import cloudinary.uploader

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('admin_logged_in'):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@csrf_exempt
@admin_required
def upload_image(request):
    """Endpoint for TinyMCE image uploads"""
    if request.method == 'POST' and request.FILES.get('file'):
        image_file = request.FILES['file']
        try:
            upload_result = cloudinary.uploader.upload(image_file)
            return JsonResponse({'location': upload_result['secure_url']})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

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
    published_blog_count = db.blogs.count_documents({'is_published': True})
    skill_count = db.skills.count_documents({})
    
    recent_blogs = list(db.blogs.find().sort('created_at', -1).limit(5))
    for b in recent_blogs:
        b['id'] = str(b['_id'])
        
    recent_projects = list(db.projects.find().sort('order', 1).limit(5))
    for p in recent_projects:
        p['id'] = str(p['_id'])
        
    return render(request, 'main/admin/dashboard.html', {
        'project_count': project_count,
        'blog_count': blog_count,
        'published_blog_count': published_blog_count,
        'skill_count': skill_count,
        'recent_blogs': recent_blogs,
        'recent_projects': recent_projects,
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
        
        if profile.get('resume_url'):
            profile_data['resume_url'] = profile['resume_url']
            
        resume_file = request.FILES.get('resume')
        if resume_file:
            upload_result = cloudinary.uploader.upload(
                resume_file, 
                public_id='portfolio_resume',
                overwrite=True,
                resource_type='auto'
            )
            profile_data['resume_url'] = upload_result['secure_url']
            
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
    from django.utils.text import slugify
    db = get_db()
    blog = {}
    if blog_id:
        blog = db.blogs.find_one({'_id': ObjectId(blog_id)})
        blog['id'] = str(blog['_id'])
        
    if request.method == 'POST':
        title = request.POST.get('title')
        blog_data = {
            'title': title,
            'slug': slugify(title),
            'content': request.POST.get('content'),
            'is_published': request.POST.get('is_published') == 'on',
        }
        
        # Keep existing image url if editing
        if blog_id and blog.get('image_url'):
            blog_data['image_url'] = blog['image_url']
            
        image_file = request.FILES.get('image')
        if image_file:
            upload_result = cloudinary.uploader.upload(image_file)
            blog_data['image_url'] = upload_result['secure_url']
            
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

@admin_required
def manage_skills(request):
    db = get_db()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        icon_class = request.POST.get('icon_class', '')
        category = request.POST.get('category', 'Other')
        
        max_order_skill = db.skills.find_one(sort=[('order', -1)])
        new_order = (max_order_skill.get('order', 0) + 1) if max_order_skill else 0
        
        skill_data = {'name': name, 'icon_class': icon_class, 'category': category, 'order': new_order}
        
        custom_icon = request.FILES.get('custom_icon')
        if custom_icon:
            upload_result = cloudinary.uploader.upload(
                custom_icon,
                folder='portfolio_skills',
                resource_type='auto'
            )
            skill_data['image_url'] = upload_result['secure_url']
            
        if name:
            db.skills.insert_one(skill_data)
        return redirect('admin_skills')
        
    skills = list(db.skills.find().sort('order', 1))
    
    # Auto-migration for existing skills without order or category
    migrated = False
    for i, s in enumerate(skills):
        updates = {}
        if 'order' not in s:
            updates['order'] = i
            s['order'] = i
        if 'category' not in s:
            updates['category'] = 'Other'
            s['category'] = 'Other'
            
        if updates:
            db.skills.update_one({'_id': s['_id']}, {'$set': updates})
            migrated = True
            
    if migrated:
        skills = list(db.skills.find().sort('order', 1))
        
    for s in skills:
        s['id'] = str(s['_id'])
        
    categories = db.skills.distinct('category')
    categories = [c for c in categories if c and c != 'Other']
        
    return render(request, 'main/admin/manage_skills.html', {'skills': skills, 'categories': categories})

@admin_required
def edit_skill(request, skill_id):
    db = get_db()
    skill = db.skills.find_one({'_id': ObjectId(skill_id)})
    if not skill:
        return redirect('admin_skills')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        icon_class = request.POST.get('icon_class', '')
        category = request.POST.get('category', 'Other')
        
        skill_data = {'name': name, 'icon_class': icon_class, 'category': category}
        
        if skill.get('image_url'):
            skill_data['image_url'] = skill['image_url']
            
        custom_icon = request.FILES.get('custom_icon')
        if custom_icon:
            upload_result = cloudinary.uploader.upload(
                custom_icon,
                folder='portfolio_skills',
                resource_type='auto'
            )
            skill_data['image_url'] = upload_result['secure_url']
            
        if name:
            db.skills.update_one({'_id': ObjectId(skill_id)}, {'$set': skill_data})
        return redirect('admin_skills')
        
    skill['id'] = str(skill['_id'])
    
    categories = db.skills.distinct('category')
    categories = [c for c in categories if c and c != 'Other']
    
    return render(request, 'main/admin/edit_skill.html', {'skill': skill, 'categories': categories})

@admin_required
def delete_skill(request, skill_id):
    db = get_db()
    if request.method == 'POST':
        db.skills.delete_one({'_id': ObjectId(skill_id)})
    return redirect('admin_skills')

@csrf_exempt
@admin_required
def reorder_skills(request):
    import json
    if request.method == 'POST':
        try:
            db = get_db()
            data = json.loads(request.body)
            for index, skill_id in enumerate(data):
                db.skills.update_one(
                    {'_id': ObjectId(skill_id)},
                    {'$set': {'order': index}}
                )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@admin_required
def list_projects(request):
    db = get_db()
    projects = list(db.projects.find().sort('order', 1))
    for p in projects:
        p['id'] = str(p['_id'])
    return render(request, 'main/admin/list_projects.html', {'projects': projects})

@admin_required
def edit_project(request, project_id=None):
    from django.utils.text import slugify
    db = get_db()
    project = {}
    if project_id:
        project = db.projects.find_one({'_id': ObjectId(project_id)})
        project['id'] = str(project['_id'])
        
    if request.method == 'POST':
        title = request.POST.get('title')
        project_data = {
            'title': title,
            'slug': slugify(title),
            'description': request.POST.get('description'),
            'tech': request.POST.get('tech'),
            'github_url': request.POST.get('github_url'),
            'live_url': request.POST.get('live_url'),
            'long_description': request.POST.get('long_description'),
            'order': int(request.POST.get('order', 0)),
        }
        
        # Keep existing image url if editing
        if project_id and project.get('image_url'):
            project_data['image_url'] = project['image_url']
            
        image_file = request.FILES.get('image')
        if image_file:
            upload_result = cloudinary.uploader.upload(image_file)
            project_data['image_url'] = upload_result['secure_url']
            
        if project_id:
            db.projects.update_one({'_id': ObjectId(project_id)}, {'$set': project_data})
        else:
            db.projects.insert_one(project_data)
            
        return redirect('admin_projects')
        
    return render(request, 'main/admin/edit_project.html', {'project': project})

@admin_required
def delete_project(request, project_id):
    db = get_db()
    if request.method == 'POST':
        db.projects.delete_one({'_id': ObjectId(project_id)})
    return redirect('admin_projects')

@admin_required
def list_messages(request):
    db = get_db()
    messages = list(db.messages.find().sort('created_at', -1))
    for m in messages:
        m['id'] = str(m['_id'])
    return render(request, 'main/admin/messages_list.html', {'messages': messages})

@admin_required
def view_message(request, message_id):
    db = get_db()
    message = db.messages.find_one({'_id': ObjectId(message_id)})
    if message:
        message['id'] = str(message['_id'])
        if not message.get('is_read'):
            db.messages.update_one({'_id': ObjectId(message_id)}, {'$set': {'is_read': True}})
    return render(request, 'main/admin/view_message.html', {'message': message})

@admin_required
def delete_message(request, message_id):
    db = get_db()
    if request.method == 'POST':
        db.messages.delete_one({'_id': ObjectId(message_id)})
    return redirect('admin_messages')

@admin_required
def admin_settings(request):
    db = get_db()
    smtp_settings = db.settings.find_one({'type': 'smtp'}) or {}
    general_settings = db.settings.find_one({'type': 'general'}) or {'max_messages': 50}
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Update General Settings
        max_msgs = int(request.POST.get('max_messages', 50))
        db.settings.update_one(
            {'type': 'general'}, 
            {'$set': {'max_messages': max_msgs}}, 
            upsert=True
        )
        
        # Update SMTP Settings
        smtp_data = {
            'type': 'smtp',
            'host': request.POST.get('host'),
            'port': int(request.POST.get('port', 587)),
            'user': request.POST.get('user'),
            'password': request.POST.get('password'),
            'from_email': request.POST.get('from_email'),
            'use_tls': request.POST.get('use_tls') == 'on',
        }
        
        db.settings.update_one(
            {'type': 'smtp'},
            {'$set': smtp_data},
            upsert=True
        )
            
        if action == 'test_email':
            # Try sending a test email
            try:
                from django.core.mail import get_connection, EmailMessage
                connection = get_connection(
                    host=smtp_data['host'],
                    port=smtp_data['port'],
                    username=smtp_data['user'],
                    password=smtp_data['password'],
                    use_tls=smtp_data['use_tls'],
                )
                email = EmailMessage(
                    'Portfolio SMTP Test',
                    'This is a test email from your portfolio website. If you received this, your SMTP settings are correct!',
                    smtp_data['from_email'],
                    [smtp_data['from_email']], # Send to self
                    connection=connection,
                )
                email.send()
                return render(request, 'main/admin/settings.html', {
                    'smtp': smtp_data,
                    'general': {'max_messages': max_msgs},
                    'success': 'Test email sent successfully! Check your inbox.',
                })
            except Exception as e:
                return render(request, 'main/admin/settings.html', {
                    'smtp': smtp_data,
                    'general': {'max_messages': max_msgs},
                    'error': f'Failed to send test email: {str(e)}',
                })
                
        return redirect('admin_settings')
        
    return render(request, 'main/admin/settings.html', {
        'smtp': smtp_settings,
        'general': general_settings
    })
