from django.db import models

"""
Note: This project is configured to use raw PyMongo and the Django database backend 
is set to 'dummy'. These models are NOT used by the ORM or any migrations. 
They exist solely for documentation purposes to provide a clear sense of the 
MongoDB collections and document structures used in this project.
"""

class Profile(models.Model):
    """Maps to the 'profile' collection (single document)."""
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    bio = models.TextField()
    email = models.EmailField()
    github = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    resume_url = models.URLField(blank=True, null=True)
    views = models.IntegerField(default=0)

    class Meta:
        managed = False


class Project(models.Model):
    """Maps to the 'projects' collection."""
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500)
    image_url = models.URLField(blank=True, null=True)
    tech = models.CharField(max_length=200)  # e.g. 'React, Node, MongoDB'
    github_url = models.URLField(blank=True, null=True)
    live_url = models.URLField(blank=True, null=True)
    long_description = models.TextField()
    order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    views = models.IntegerField(default=0)

    class Meta:
        managed = False


class Skill(models.Model):
    """Maps to the 'skills' collection."""
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=100, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=100, default='Other')
    order = models.IntegerField(default=0)

    class Meta:
        managed = False


class Blog(models.Model):
    """Maps to the 'blogs' collection."""
    title = models.CharField(max_length=200)
    image_url = models.URLField(blank=True, null=True)
    content = models.TextField()
    tags = models.CharField(max_length=200, blank=True, null=True)  # Comma-separated list of tags
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.IntegerField(default=0)

    class Meta:
        managed = False


class PageView(models.Model):
    """
    Maps to the 'page_views' collection.
    Records individual page view events with timestamps for analytics.
    """
    type = models.CharField(max_length=50)  # 'homepage', 'project', 'blog'
    item_id = models.CharField(max_length=50, blank=True, null=True)  # string representing ObjectId if project/blog
    item_title = models.CharField(max_length=200, blank=True, null=True)  # e.g., 'E-Commerce Platform' or 'Intro to Django'
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False


class Education(models.Model):
    """Maps to the 'education' collection."""
    institution = models.CharField(max_length=200)
    institution_url = models.URLField(blank=True, null=True)
    degree = models.CharField(max_length=200) # e.g. B.Tech, SSC, HSC
    start_date = models.CharField(max_length=50) # Allow strings like 'Aug 2018'
    end_date = models.CharField(max_length=50, blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        managed = False


class Experience(models.Model):
    """Maps to the 'experience' collection."""
    company = models.CharField(max_length=200)
    company_url = models.URLField(blank=True, null=True)
    role = models.CharField(max_length=200)
    start_date = models.CharField(max_length=50)
    end_date = models.CharField(max_length=50, blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        managed = False

