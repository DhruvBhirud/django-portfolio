from django.shortcuts import render
from .db import get_db
from bson import ObjectId

def index(request):
    db = get_db()
    projects = list(db.projects.find().sort('order', 1))
    skills = list(db.skills.find())
    
    # Get published blogs for index
    blogs = list(db.blogs.find({'is_published': True}).sort('created_at', -1).limit(3))
    
    # Get profile
    profile = db.profile.find_one() or {}
    
    # Convert ObjectId to string for template use
    for p in projects:
        p['id'] = str(p['_id'])
    for b in blogs:
        b['id'] = str(b['_id'])
    
    context = {
        'projects': projects,
        'skills': skills,
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

def project_detail(request, project_id):
    db = get_db()
    project = db.projects.find_one({'_id': ObjectId(project_id)})
    if project:
        project['id'] = str(project['_id'])
    return render(request, 'main/project_detail.html', {'project': project})

def blog_index(request):
    db = get_db()
    blogs = list(db.blogs.find({'is_published': True}).sort('created_at', -1))
    for b in blogs:
        b['id'] = str(b['_id'])
    return render(request, 'main/blog_index.html', {'blogs': blogs})

def blog_detail(request, blog_id):
    db = get_db()
    blog = db.blogs.find_one({'_id': ObjectId(blog_id)})
    if blog:
        blog['id'] = str(blog['_id'])
    return render(request, 'main/blog_detail.html', {'blog': blog})