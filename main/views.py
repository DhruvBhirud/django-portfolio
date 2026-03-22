from django.shortcuts import render, redirect
from .db import get_db
from bson import ObjectId
from django.contrib import messages
from datetime import datetime
import json

def index(request):
    db = get_db()
    projects = list(db.projects.find().sort('order', 1))
    raw_skills = list(db.skills.find().sort('order', 1))
    
    # Group skills by category while maintaining explicit sort order per-category
    grouped_skills = {}
    for skill in raw_skills:
        cat = skill.get('category', 'Other')
        if cat not in grouped_skills:
            grouped_skills[cat] = []
        grouped_skills[cat].append(skill)
    
    # Get published blogs for index
    blogs = list(db.blogs.find({'is_published': True}).sort('created_at', -1).limit(3))
    
    # Get profile
    profile = db.profile.find_one() or {}
    
    from django.utils.text import slugify
    
    # Convert ObjectId to string for template use, and auto-heal missing slugs
    for p in projects:
        p['id'] = str(p['_id'])
        if 'slug' not in p:
            p['slug'] = slugify(p.get('title', p['id']))
            db.projects.update_one({'_id': p['_id']}, {'$set': {'slug': p['slug']}})
            
    for b in blogs:
        b['id'] = str(b['_id'])
        if 'slug' not in b:
            b['slug'] = slugify(b.get('title', b['id']))
            db.blogs.update_one({'_id': b['_id']}, {'$set': {'slug': b['slug']}})
    
    context = {
        'projects': projects,
        'grouped_skills': grouped_skills,
        'blogs': blogs,
        'name': profile.get('name', 'Dhruv Bhirud'),
        'title': profile.get('title', 'Software Developer'),
        'bio': profile.get('bio', 'Passionate developer who loves building things.'),
        'email': profile.get('email', 'bhiruddhruv@gmail.com'),
        'github': profile.get('github', 'https://github.com/yourusername'),
        'linkedin': profile.get('linkedin', 'https://linkedin.com/in/yourusername'),
        'resume_url': profile.get('resume_url', ''),
    }
    return render(request, 'main/index.html', context)

def project_detail(request, project_slug):
    db = get_db()
    project = db.projects.find_one({'slug': project_slug})
    if project:
        project['id'] = str(project['_id'])
    return render(request, 'main/project_detail.html', {'project': project})

def blog_index(request):
    from django.utils.text import slugify
    db = get_db()
    blogs = list(db.blogs.find({'is_published': True}).sort('created_at', -1))
    for b in blogs:
        b['id'] = str(b['_id'])
        if 'slug' not in b:
            b['slug'] = slugify(b.get('title', b['id']))
            db.blogs.update_one({'_id': b['_id']}, {'$set': {'slug': b['slug']}})
    return render(request, 'main/blog_index.html', {'blogs': blogs})

def blog_detail(request, blog_slug):
    db = get_db()
    blog = db.blogs.find_one({'slug': blog_slug})
    if blog:
        blog['id'] = str(blog['_id'])
    return render(request, 'main/blog_detail.html', {'blog': blog})

def send_admin_notification(message_data):
    """Helper to send email notification using DB-stored SMTP settings."""
    db = get_db()
    smtp = db.settings.find_one({'type': 'smtp'})
    profile = db.profile.find_one() or {}
    admin_email = profile.get('email', 'bhiruddhruv@gmail.com')
    
    if not smtp or not admin_email:
        return False
        
    try:
        from django.core.mail import get_connection, EmailMessage
        connection = get_connection(
            host=smtp['host'],
            port=smtp['port'],
            username=smtp['user'],
            password=smtp['password'],
            use_tls=smtp.get('use_tls', True),
        )
        subject = f"New Portfolio Message: {message_data['subject']}"
        body = f"You have received a new message from your portfolio website.\n\n" \
               f"Name: {message_data['name']}\n" \
               f"Email: {message_data['email']}\n" \
               f"Subject: {message_data['subject']}\n\n" \
               f"Message:\n{message_data['message']}"
               
        email = EmailMessage(
            subject,
            body,
            smtp['from_email'],
            [admin_email],
            connection=connection,
        )
        email.send()
        return True
    except Exception as e:
        print(f"SMTP Notification failed: {e}")
        return False

def submit_contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        if not name or not email or not message_text:
            messages.error(request, "Please fill in all required fields.")
            return redirect('index')
            
        message_data = {
            'name': name,
            'email': email,
            'subject': subject or 'No Subject',
            'message': message_text,
            'created_at': datetime.now(),
            'is_read': False
        }
        
        db = get_db()
        db.messages.insert_one(message_data)
        
        # Enforce storage limit
        settings_doc = db.settings.find_one({'type': 'general'}) or {}
        max_msgs = settings_doc.get('max_messages', 50)
        
        current_count = db.messages.count_documents({})
        if current_count > max_msgs:
            # Find and delete oldest messages
            to_delete_count = current_count - max_msgs
            oldest_docs = list(db.messages.find({}, {'_id': 1}).sort('created_at', 1).limit(to_delete_count))
            oldest_ids = [doc['_id'] for doc in oldest_docs]
            db.messages.delete_many({'_id': {'$in': oldest_ids}})
        
        # Trigger notification
        send_admin_notification(message_data)
        
        messages.success(request, "Thank you! Your message has been sent successfully.")
        return redirect('index')
        
    return redirect('index')