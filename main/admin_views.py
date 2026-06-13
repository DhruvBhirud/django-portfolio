from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import json
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
        from django.contrib.auth.hashers import make_password, check_password
        password = request.POST.get('password')
        
        db = get_db()
        auth_doc = db.settings.find_one({'type': 'admin_auth'})
        if not auth_doc:
            # Fallback to settings.ADMIN_PASSWORD on first login and save its hash
            fallback_password = getattr(settings, 'ADMIN_PASSWORD', 'admin123')
            current_hash = make_password(fallback_password)
            db.settings.update_one(
                {'type': 'admin_auth'},
                {'$set': {'password_hash': current_hash}},
                upsert=True
            )
        else:
            current_hash = auth_doc.get('password_hash')
            
        if check_password(password, current_hash):
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
    education_count = db.education.count_documents({})
    experience_count = db.experience.count_documents({})
    
    # Calculate aggregate view statistics
    total_blog_views = sum(b.get('views', 0) for b in db.blogs.find({}, {'views': 1}))
    total_project_views = sum(p.get('views', 0) for p in db.projects.find({}, {'views': 1}))
    
    # Retrieve homepage views from Profile
    profile = db.profile.find_one() or {}
    homepage_views = profile.get('views', 0)
    
    recent_blogs = list(db.blogs.find().sort('created_at', -1).limit(5))
    for b in recent_blogs:
        b['id'] = str(b['_id'])
        
    recent_projects = list(db.projects.find().sort('order', 1).limit(5))
    for p in recent_projects:
        p['id'] = str(p['_id'])
        
    # Fetch most viewed (popular) blogs and projects
    popular_blogs = list(db.blogs.find().sort('views', -1).limit(5))
    for b in popular_blogs:
        b['id'] = str(b['_id'])
        b['views'] = b.get('views', 0)
        
    popular_projects = list(db.projects.find().sort('views', -1).limit(5))
    for p in popular_projects:
        p['id'] = str(p['_id'])
        p['views'] = p.get('views', 0)
        
    # --- Page View Analytics Processing ---
    end_date = datetime.now()
    start_date = end_date - timedelta(days=29)
    start_day_midnight = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
    
    # Fetch page views for the last 30 days
    views_cursor = list(db.page_views.find({
        'timestamp': {'$gte': start_day_midnight}
    }))
    
    # Initialize daily stats
    daily_stats = {}
    temp_date = start_date
    while temp_date <= end_date:
        date_str = temp_date.strftime('%Y-%m-%d')
        daily_stats[date_str] = {'homepage': 0, 'project': 0, 'blog': 0, 'total': 0}
        temp_date += timedelta(days=1)
        
    # Aggregate counts
    for pv in views_cursor:
        ts = pv.get('timestamp')
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    continue
            date_str = ts.strftime('%Y-%m-%d')
            if date_str in daily_stats:
                pv_type = pv.get('type', 'homepage')
                if pv_type in ['homepage', 'project', 'blog']:
                    daily_stats[date_str][pv_type] += 1
                daily_stats[date_str]['total'] += 1
                
    chart_dates = sorted(daily_stats.keys())
    chart_homepage = [daily_stats[d]['homepage'] for d in chart_dates]
    chart_project = [daily_stats[d]['project'] for d in chart_dates]
    chart_blog = [daily_stats[d]['blog'] for d in chart_dates]
    chart_total = [daily_stats[d]['total'] for d in chart_dates]
    
    chart_data = {
        'dates': chart_dates,
        'homepage': chart_homepage,
        'project': chart_project,
        'blog': chart_blog,
        'total': chart_total,
    }
    chart_data_json = json.dumps(chart_data)
    
    # Fetch 10 most recent views
    recent_views = list(db.page_views.find().sort('timestamp', -1).limit(10))
    for rv in recent_views:
        rv['id'] = str(rv['_id'])
        ts = rv.get('timestamp')
        if isinstance(ts, datetime):
            rv['formatted_time'] = ts.strftime('%b %d, %Y %H:%M:%S')
        else:
            rv['formatted_time'] = str(ts)
        
    return render(request, 'main/admin/dashboard.html', {
        'project_count': project_count,
        'blog_count': blog_count,
        'published_blog_count': published_blog_count,
        'skill_count': skill_count,
        'education_count': education_count,
        'experience_count': experience_count,
        'homepage_views': homepage_views,
        'total_blog_views': total_blog_views,
        'total_project_views': total_project_views,
        'total_views': homepage_views + total_blog_views + total_project_views,
        'recent_blogs': recent_blogs,
        'recent_projects': recent_projects,
        'popular_blogs': popular_blogs,
        'popular_projects': popular_projects,
        'chart_data_json': chart_data_json,
        'recent_views': recent_views,
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
            'tags': request.POST.get('tags', ''),
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
            'is_featured': request.POST.get('is_featured') == 'on',
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
def list_education(request):
    db = get_db()
    education_list = list(db.education.find().sort('order', 1))
    for e in education_list:
        e['id'] = str(e['_id'])
    return render(request, 'main/admin/list_education.html', {'education_list': education_list})

@admin_required
def edit_education(request, education_id=None):
    db = get_db()
    education = {}
    if education_id:
        education = db.education.find_one({'_id': ObjectId(education_id)})
        education['id'] = str(education['_id'])
        
    if request.method == 'POST':
        education_data = {
            'institution': request.POST.get('institution'),
            'institution_url': request.POST.get('institution_url'),
            'degree': request.POST.get('degree'),
            'start_date': request.POST.get('start_date'),
            'end_date': request.POST.get('end_date'),
            'is_current': request.POST.get('is_current') == 'on',
            'description': request.POST.get('description'),
        }
            
        if education_id:
            db.education.update_one({'_id': ObjectId(education_id)}, {'$set': education_data})
        else:
            max_doc = db.education.find_one(sort=[('order', -1)])
            education_data['order'] = (max_doc.get('order', 0) + 1) if max_doc else 0
            db.education.insert_one(education_data)
            
        return redirect('admin_education')
        
    return render(request, 'main/admin/edit_education.html', {'education': education})

@admin_required
def delete_education(request, education_id):
    db = get_db()
    if request.method == 'POST':
        db.education.delete_one({'_id': ObjectId(education_id)})
    return redirect('admin_education')

@csrf_exempt
@admin_required
def reorder_education(request):
    if request.method == 'POST':
        try:
            db = get_db()
            data = json.loads(request.body)
            for index, education_id in enumerate(data):
                db.education.update_one(
                    {'_id': ObjectId(education_id)},
                    {'$set': {'order': index}}
                )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@admin_required
def list_experience(request):
    db = get_db()
    experience_list = list(db.experience.find().sort('order', 1))
    for e in experience_list:
        e['id'] = str(e['_id'])
    return render(request, 'main/admin/list_experience.html', {'experience_list': experience_list})

@admin_required
def edit_experience(request, experience_id=None):
    db = get_db()
    experience = {}
    if experience_id:
        experience = db.experience.find_one({'_id': ObjectId(experience_id)})
        experience['id'] = str(experience['_id'])
        
    if request.method == 'POST':
        experience_data = {
            'company': request.POST.get('company'),
            'company_url': request.POST.get('company_url'),
            'role': request.POST.get('role'),
            'start_date': request.POST.get('start_date'),
            'end_date': request.POST.get('end_date'),
            'is_current': request.POST.get('is_current') == 'on',
            'description': request.POST.get('description'),
        }
            
        if experience_id:
            db.experience.update_one({'_id': ObjectId(experience_id)}, {'$set': experience_data})
        else:
            # Assign max order + 1 if new
            max_doc = db.experience.find_one(sort=[('order', -1)])
            experience_data['order'] = (max_doc.get('order', 0) + 1) if max_doc else 0
            db.experience.insert_one(experience_data)
            
        return redirect('admin_experience')
        
    return render(request, 'main/admin/edit_experience.html', {'experience': experience})

@admin_required
def delete_experience(request, experience_id):
    db = get_db()
    if request.method == 'POST':
        db.experience.delete_one({'_id': ObjectId(experience_id)})
    return redirect('admin_experience')

@csrf_exempt
@admin_required
def reorder_experience(request):
    if request.method == 'POST':
        try:
            db = get_db()
            data = json.loads(request.body)
            for index, experience_id in enumerate(data):
                db.experience.update_one(
                    {'_id': ObjectId(experience_id)},
                    {'$set': {'order': index}}
                )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

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
        
        if action == 'change_password':
            from django.contrib.auth.hashers import make_password, check_password
            current_pwd = request.POST.get('current_password')
            new_pwd = request.POST.get('new_password')
            confirm_pwd = request.POST.get('confirm_password')
            
            auth_doc = db.settings.find_one({'type': 'admin_auth'})
            if not auth_doc:
                fallback_password = getattr(settings, 'ADMIN_PASSWORD', 'admin123')
                current_hash = make_password(fallback_password)
            else:
                current_hash = auth_doc.get('password_hash')
                
            if not check_password(current_pwd, current_hash):
                return render(request, 'main/admin/settings.html', {
                    'smtp': smtp_settings,
                    'general': general_settings,
                    'error': 'Incorrect current password.',
                })
                
            if new_pwd != confirm_pwd:
                return render(request, 'main/admin/settings.html', {
                    'smtp': smtp_settings,
                    'general': general_settings,
                    'error': 'New passwords do not match.',
                })
                
            new_hash = make_password(new_pwd)
            db.settings.update_one(
                {'type': 'admin_auth'},
                {'$set': {'password_hash': new_hash}},
                upsert=True
            )
            return render(request, 'main/admin/settings.html', {
                'smtp': smtp_settings,
                'general': general_settings,
                'success': 'Password updated successfully!',
            })
        
        # Update General Settings
        max_msgs = int(request.POST.get('max_messages', 50))
        turnstile_site_key = request.POST.get('turnstile_site_key', '').strip()
        turnstile_secret_key = request.POST.get('turnstile_secret_key', '').strip()
        db.settings.update_one(
            {'type': 'general'}, 
            {'$set': {
                'max_messages': max_msgs,
                'turnstile_site_key': turnstile_site_key,
                'turnstile_secret_key': turnstile_secret_key,
            }}, 
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
            if not smtp_data['host'] or not smtp_data['from_email']:
                return render(request, 'main/admin/settings.html', {
                    'smtp': smtp_data,
                    'general': {'max_messages': max_msgs},
                    'error': 'To send a test email, SMTP Host and From Email are required.',
                })
            
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


@admin_required
def list_endorsements(request):
    db = get_db()
    skills = list(db.skills.find())
    
    pending_endorsements = []
    approved_endorsements = []
    
    for skill in skills:
        skill_id_str = str(skill['_id'])
        skill_name = skill.get('name', 'Unknown Skill')
        for endorser in skill.get('endorsers', []):
            created = endorser.get('created_at')
            created_str = ""
            if isinstance(created, datetime):
                created_str = created.strftime('%b %d, %Y %H:%M')
            elif isinstance(created, str):
                created_str = created
            
            item = {
                'skill_id': skill_id_str,
                'skill_name': skill_name,
                'id': endorser.get('id', ''),
                'name': endorser.get('name', ''),
                'comment': endorser.get('comment', ''),
                'created_at': created_str,
                'raw_created': created if isinstance(created, datetime) else datetime.min,
                'approved': endorser.get('approved', True)
            }
            
            if item['approved']:
                approved_endorsements.append(item)
            else:
                pending_endorsements.append(item)
                
    # Sort by raw_created descending (newest first)
    pending_endorsements.sort(key=lambda x: x['raw_created'], reverse=True)
    approved_endorsements.sort(key=lambda x: x['raw_created'], reverse=True)
    
    return render(request, 'main/admin/manage_endorsements.html', {
        'pending': pending_endorsements,
        'approved': approved_endorsements
    })


@admin_required
def approve_endorse_skill(request, skill_id, endorsement_id):
    if request.method == 'POST':
        db = get_db()
        db.skills.update_one(
            {'_id': ObjectId(skill_id), 'endorsers.id': endorsement_id},
            {
                '$set': {'endorsers.$.approved': True},
                '$inc': {'endorsements': 1}
            }
        )
    return redirect('admin_endorsements')


@admin_required
def delete_endorse_skill(request, skill_id, endorsement_id):
    if request.method == 'POST':
        db = get_db()
        skill = db.skills.find_one({'_id': ObjectId(skill_id)})
        if skill:
            endorsement = next((e for e in skill.get('endorsers', []) if e.get('id') == endorsement_id), None)
            if endorsement:
                was_approved = endorsement.get('approved', True)
                dec_value = -1 if was_approved else 0
                db.skills.update_one(
                    {'_id': ObjectId(skill_id)},
                    {
                        '$pull': {'endorsers': {'id': endorsement_id}},
                        '$inc': {'endorsements': dec_value}
                    }
                )
    return redirect('admin_endorsements')

@admin_required
def manage_theme(request):
    db = get_db()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save':
            theme_data = {
                'primary': request.POST.get('primary'),
                'bg_main': request.POST.get('bg_main'),
                'bg_alt': request.POST.get('bg_alt'),
                'bg_card': request.POST.get('bg_card'),
                'text_main': request.POST.get('text_main'),
                'text_muted': request.POST.get('text_muted'),
                'bg_nav': request.POST.get('bg_nav'),
                'border_color': request.POST.get('border_color'),
                'border_card': request.POST.get('border_card'),
                
                'light_bg_main': request.POST.get('light_bg_main'),
                'light_bg_alt': request.POST.get('light_bg_alt'),
                'light_bg_card': request.POST.get('light_bg_card'),
                'light_text_main': request.POST.get('light_text_main'),
                'light_text_muted': request.POST.get('light_text_muted'),
                'light_bg_nav': request.POST.get('light_bg_nav'),
                'light_border_color': request.POST.get('light_border_color'),
                'light_border_card': request.POST.get('light_border_card'),
            }
            # Add or update theme document
            db.theme.update_one({}, {'$set': theme_data}, upsert=True)
        elif action == 'reset':
            # Delete theme document to revert to default CSS
            db.theme.delete_many({})
        return redirect('admin_theme')
        
    theme = db.theme.find_one() or {}
    
    # Default values based on current style.css
    defaults = {
        'primary': '#6c63ff',
        'bg_main': '#0a0a0a',
        'bg_alt': '#111111',
        'bg_card': '#1a1a2e',
        'text_main': '#e0e0e0',
        'text_muted': '#888888',
        'bg_nav': 'rgba(10, 10, 10, 0.95)',
        'border_color': '#222222',
        'border_card': '#2a2a4a',
        
        'light_bg_main': '#f8f9fa',
        'light_bg_alt': '#e9ecef',
        'light_bg_card': '#ffffff',
        'light_text_main': '#212529',
        'light_text_muted': '#6c757d',
        'light_bg_nav': 'rgba(255, 255, 255, 0.95)',
        'light_border_color': '#dee2e6',
        'light_border_card': '#e5e7eb',
    }
    
    # If a value is missing in db, fallback to default for template rendering
    for k, v in defaults.items():
        if k not in theme:
            theme[k] = v
            
    return render(request, 'main/admin/manage_theme.html', {'theme': theme})
