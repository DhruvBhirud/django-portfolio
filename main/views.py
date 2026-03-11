from django.shortcuts import render
from .db import get_db
from bson import ObjectId

def index(request):
    db = get_db()
    projects = list(db.projects.find().sort('order', 1))
    skills = list(db.skills.find())
    
    # Convert ObjectId to string for template use
    for p in projects:
        p['id'] = str(p['_id'])
        del p['_id']
    
    context = {
        'projects': projects,
        'skills': skills,
        'name': 'Dhruv Bhirud',
        'title': 'Software Developer',
        'bio': 'Passionate developer who loves building things.',
        'email': 'bhiruddhruv@gmail.com',
        'github': 'https://github.com/yourusername',
        'linkedin': 'https://linkedin.com/in/yourusername',
    }
    return render(request, 'main/index.html', context)

def project_detail(request, project_id):
    db = get_db()
    project = db.projects.find_one({'_id': ObjectId(project_id)})
    if project:
        project['id'] = str(project['_id'])
        del project['_id']
    return render(request, 'main/project_detail.html', {'project': project})