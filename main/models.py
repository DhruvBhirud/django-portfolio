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
    github = models.URLField()
    linkedin = models.URLField()

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

    class Meta:
        managed = False


class Skill(models.Model):
    """Maps to the 'skills' collection."""
    name = models.CharField(max_length=100)

    class Meta:
        managed = False


class Blog(models.Model):
    """Maps to the 'blogs' collection."""
    title = models.CharField(max_length=200)
    image_url = models.URLField(blank=True, null=True)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
