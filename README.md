# Django Personal Portfolio

A fast, responsive, and dynamic personal portfolio website built with Django and MongoDB, tailored for showcasing projects, skills, and blog posts. Unlike traditional Django setups, this project leverages **PyMongo** directly for maximum flexibility and performance with a non-relational database.

## 🚀 Features

- **Project Showcase:** Display your top projects with images, technologies used, GitHub links, and live demo URLs. Projects are highly customizable with detailed descriptions.
- **Skills Categorization:** Visually group your skills by category (e.g., Frontend, Backend, Tools) based dynamically on database records.
- **Integrated Blog:** Write and publish markdown/HTML blog posts right on your portfolio. Handles slugs and publishing status automatically.
- **MongoDB Integration (PyMongo):** Bypasses the default Django ORM in favor of raw PyMongo for a purely unstructured document database approach.
- **Cloudinary Storage:** Managed media storage for images natively through Cloudinary APIs.
- **Vercel Ready:** Fully configured with a `vercel.json` file for immediate serverless deployments.

## 🛠️ Technology Stack

- **Backend:** Django 5.2, Python 3.12
- **Database:** MongoDB (via `pymongo`)
- **Frontend:** Django Templates, HTML, CSS, JavaScript
- **Static files:** WhiteNoise
- **Media Hosting:** Cloudinary
- **Deployment:** Vercel

## ⚙️ Local Development Setup

Follow these instructions to run the application locally.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/django-portfolio.git
cd django-portfolio
```

### 2. Set Up a Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add the following context (update the values with your actual credentials):

```env
# Django
SECRET_KEY=your-django-secret-key
DEBUG=True

# MongoDB
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/myFirstDatabase?retryWrites=true&w=majority

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Admin (Optional but recommended)
ADMIN_PASSWORD=your_secure_password
```

### 5. Run the Application
Since this project does not use the Django ORM, you do **not** need to run `makemigrations` or `migrate`. Just start the server!

```bash
python manage.py runserver
```

Navigate to `http://127.0.0.1:8000/` in your browser to view the portfolio.

## 🗄️ Database Seeding & Maintenance

To quickly populate your MongoDB collections with sample data (projects, skills, blogs), you can run the included seed script. Make sure your virtual environment is activated and you have a valid `MONGODB_URI` in your `.env`.

```bash
python seed_db.py
```

*Note: You can also use `backfill_slugs.py` to auto-generate slugs for earlier database entries that might be missing them.*

## 🚀 Deployment

The project is natively configured for deployment on Vercel via the included `vercel.json` configuration. Simply import your GitHub repository into Vercel, assign the environment variables in your project settings, and deploy! The `@vercel/python` builder will automatically handle routing and scaling.