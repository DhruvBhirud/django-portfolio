import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.environ['MONGODB_URI'])
db = client['portfolio_db']

# Clear existing
db.projects.drop()
db.skills.drop()

# Insert projects
db.projects.insert_many([
    {
        'title': 'E-Commerce Platform',
        'description': 'Full-stack shopping app with cart, auth, and payments.',
        'tech': 'Django',
        'github_url': 'https://github.com/yourname/ecommerce',
        'live_url': '',
        'long_description': 'A complete e-commerce solution built with Django and integrated with Stripe for payments.',
        'order': 1
    },
    {
        'title': 'Weather Dashboard',
        'description': 'Real-time weather app using OpenWeatherMap API.',
        'tech': 'React',
        'github_url': 'https://github.com/yourname/weather',
        'live_url': 'https://weather-app.vercel.app',
        'long_description': 'Beautiful weather dashboard with 7-day forecasts and location search.',
        'order': 2
    },
])

# Insert skills
db.skills.insert_many([
    {'name': 'Python'}, {'name': 'Django'}, {'name': 'MongoDB'},
    {'name': 'JavaScript'}, {'name': 'React'}, {'name': 'PostgreSQL'},
    {'name': 'Docker'}, {'name': 'Git'}, {'name': 'REST APIs'},
])

print("✅ Database seeded!")