from django.shortcuts import render
from .db import get_db
from bson import ObjectId

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