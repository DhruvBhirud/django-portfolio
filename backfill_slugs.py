import os
import django
from bson import ObjectId
from django.utils.text import slugify

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio.settings')
django.setup()

from main.db import get_db

db = get_db()

# Backfill projects
projects = db.projects.find()
for p in projects:
    if 'title' in p:
        slug = slugify(p['title'])
        db.projects.update_one({'_id': p['_id']}, {'$set': {'slug': slug}})
        print(f"Project '{p['title']}' updated with slug: {slug}")

# Backfill blogs
blogs = db.blogs.find()
for b in blogs:
    if 'title' in b:
        slug = slugify(b['title'])
        db.blogs.update_one({'_id': b['_id']}, {'$set': {'slug': slug}})
        print(f"Blog '{b['title']}' updated with slug: {slug}")

print("Backfill complete.")
