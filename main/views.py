from django.shortcuts import render, redirect
from .db import get_db
from bson import ObjectId
from django.contrib import messages
from datetime import datetime
import json
import re
from better_profanity import profanity
from .decorators import ratelimit_post

def calculate_read_time(content_html):
    """Calculates read time based on 200 words per minute (WPM)."""
    if not content_html:
        return 1
    # Strip HTML tags
    clean_text = re.sub(r'<[^>]*>', '', content_html)
    words = clean_text.split()
    word_count = len(words)
    read_time = (word_count + 199) // 200  # Round up division
    return max(1, read_time)

def record_page_view(view_type, item_id=None, item_title=None):
    """Inserts a page view event with timestamp to MongoDB."""
    try:
        db = get_db()
        if item_id:
            item_id = str(item_id)
        
        view_doc = {
            'type': view_type,
            'item_id': item_id,
            'item_title': item_title,
            'timestamp': datetime.now()
        }
        db.page_views.insert_one(view_doc)
    except Exception as e:
        print(f"Error recording page view: {e}")

def index(request):
    db = get_db()
    # Sort by featured projects first, then by display order
    projects = list(db.projects.find().sort([('is_featured', -1), ('order', 1)]))
    raw_skills = list(db.skills.find().sort('order', 1))
    
    # Group skills by category while maintaining explicit sort order per-category
    grouped_skills = {}
    for skill in raw_skills:
        skill['id'] = str(skill['_id'])
        
        # Serialize approved endorsers list
        endorsers_list = []
        for endorser in skill.get('endorsers', []):
            if endorser.get('approved', True) is True:
                created = endorser.get('created_at')
                created_str = ""
                if isinstance(created, datetime):
                    created_str = created.strftime('%b %d, %Y')
                elif isinstance(created, str):
                    created_str = created
                endorsers_list.append({
                    'name': endorser.get('name', ''),
                    'comment': endorser.get('comment', ''),
                    'created_at': created_str
                })
        skill['endorsements'] = len(endorsers_list)
        skill['endorsers_json'] = json.dumps(endorsers_list)
        
        cat = skill.get('category', 'Other')
        if cat not in grouped_skills:
            grouped_skills[cat] = []
        grouped_skills[cat].append(skill)
    
    # Get published blogs for index
    blogs = list(db.blogs.find({'is_published': True}).sort('created_at', -1).limit(3))
    
    # Increment profile (homepage) view count
    db.profile.update_one({}, {'$inc': {'views': 1}}, upsert=True)
    record_page_view('homepage', item_title='Homepage')
    
    # Get profile
    profile = db.profile.find_one() or {}
    
    from django.utils.text import slugify
    
    # Extract unique technologies from projects for frontend client-side filtering
    all_techs = set()
    
    # Convert ObjectId to string for template use, and auto-heal missing slugs
    for p in projects:
        p['id'] = str(p['_id'])
        if 'slug' not in p:
            p['slug'] = slugify(p.get('title', p['id']))
            db.projects.update_one({'_id': p['_id']}, {'$set': {'slug': p['slug']}})
            
        tech_str = p.get('tech', '')
        tech_list = [t.strip() for t in tech_str.split(',') if t.strip()]
        p['tech_list'] = tech_list
        for t in tech_list:
            all_techs.add(t)
            
    for b in blogs:
        b['id'] = str(b['_id'])
        b['read_time'] = calculate_read_time(b.get('content', ''))
        if 'slug' not in b:
            b['slug'] = slugify(b.get('title', b['id']))
            db.blogs.update_one({'_id': b['_id']}, {'$set': {'slug': b['slug']}})
    
    # Get general settings for Turnstile Site Key
    general_settings = db.settings.find_one({'type': 'general'}) or {}
    from django.conf import settings
    turnstile_site_key = general_settings.get('turnstile_site_key') or getattr(settings, 'TURNSTILE_SITE_KEY', '1x00000000000000000000AA')
    
    # Fetch education and experience
    education_list = list(db.education.find().sort('order', 1))
    for e in education_list:
        e['id'] = str(e['_id'])
        
    experience_list = list(db.experience.find().sort('order', 1))
    for e in experience_list:
        e['id'] = str(e['_id'])
    
    context = {
        'projects': projects,
        'all_techs': sorted(list(all_techs)),
        'grouped_skills': grouped_skills,
        'blogs': blogs,
        'education_list': education_list,
        'experience_list': experience_list,
        'name': profile.get('name', 'Dhruv Bhirud'),
        'title': profile.get('title', 'Software Developer'),
        'bio': profile.get('bio', 'Passionate developer who loves building things.'),
        'email': profile.get('email', 'bhiruddhruv@gmail.com'),
        'github': profile.get('github', 'https://github.com/yourusername'),
        'linkedin': profile.get('linkedin', 'https://linkedin.com/in/yourusername'),
        'resume_url': profile.get('resume_url', ''),
        'turnstile_site_key': turnstile_site_key,
    }
    return render(request, 'main/index.html', context)

def project_detail(request, project_slug):
    db = get_db()
    # Increment view counter
    db.projects.update_one({'slug': project_slug}, {'$inc': {'views': 1}})
    project = db.projects.find_one({'slug': project_slug})
    if project:
        project['id'] = str(project['_id'])
        record_page_view('project', item_id=project['id'], item_title=project.get('title'))
    return render(request, 'main/project_detail.html', {'project': project})

def blog_index(request):
    from django.utils.text import slugify
    db = get_db()
    
    # Get search query and tag filter
    search_term = request.GET.get('q', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    
    query = {'is_published': True}
    if search_term:
        query['$or'] = [
            {'title': {'$regex': search_term, '$options': 'i'}},
            {'content': {'$regex': search_term, '$options': 'i'}}
        ]
    if tag_filter:
        query['tags'] = {'$regex': rf'(?:^|,)\s*{tag_filter}\s*(?:,|$)', '$options': 'i'}
        
    # Get total count for pagination before reading records
    total_count = db.blogs.count_documents(query)
    
    # Configure pagination
    per_page = 6
    total_pages = (total_count + per_page - 1) // per_page
    if total_pages < 1:
        total_pages = 1
        
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
        
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
        
    skip = (page - 1) * per_page
    
    # Fetch subset from database
    blogs = list(db.blogs.find(query).sort('created_at', -1).skip(skip).limit(per_page))
    
    # Auto-heal missing slugs and split tags into a list for rendering
    for b in blogs:
        b['id'] = str(b['_id'])
        b['read_time'] = calculate_read_time(b.get('content', ''))
        if 'slug' not in b:
            b['slug'] = slugify(b.get('title', b['id']))
            db.blogs.update_one({'_id': b['_id']}, {'$set': {'slug': b['slug']}})
            
        raw_tags = b.get('tags', '')
        b['tag_list'] = [t.strip() for t in raw_tags.split(',') if t.strip()] if raw_tags else []
            
    # Get all distinct tags for the sidebar filter
    all_tags = set()
    for doc in db.blogs.find({'is_published': True, 'tags': {'$exists': True, '$ne': ''}}, {'tags': 1}):
        for t in doc.get('tags', '').split(','):
            cleaned = t.strip()
            if cleaned:
                all_tags.add(cleaned)
    sorted_tags = sorted(list(all_tags))
            
    context = {
        'blogs': blogs,
        'q': search_term,
        'selected_tag': tag_filter,
        'all_tags': sorted_tags,
        'page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'previous_page_number': page - 1,
        'has_next': page < total_pages,
        'next_page_number': page + 1,
        'pages_range': range(1, total_pages + 1),
    }
    return render(request, 'main/blog_index.html', context)

def blog_detail(request, blog_slug):
    db = get_db()
    # Increment view counter
    db.blogs.update_one({'slug': blog_slug}, {'$inc': {'views': 1}})
    blog = db.blogs.find_one({'slug': blog_slug})
    if blog:
        blog['id'] = str(blog['_id'])
        blog['read_time'] = calculate_read_time(blog.get('content', ''))
        raw_tags = blog.get('tags', '')
        blog['tag_list'] = [t.strip() for t in raw_tags.split(',') if t.strip()] if raw_tags else []
        record_page_view('blog', item_id=blog['id'], item_title=blog.get('title'))
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
            reply_to=[message_data['email']]
        )
        email.send()
        return True
    except Exception as e:
        print(f"SMTP Notification failed: {e}")
        return False

@ratelimit_post(limit=3, period=300)
def submit_contact(request):
    if request.method == 'POST':
        db = get_db()
        general_settings = db.settings.find_one({'type': 'general'}) or {}
        from django.conf import settings
        turnstile_secret_key = general_settings.get('turnstile_secret_key') or getattr(settings, 'TURNSTILE_SECRET_KEY', '1x0000000000000000000000000000000AA')
        
        # Verify Turnstile response
        turnstile_response = request.POST.get('cf-turnstile-response')
        if not turnstile_response:
            messages.error(request, "CAPTCHA verification is required. Please try again.")
            return redirect('index')
            
        import urllib.request
        import urllib.parse
        
        verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        post_data = urllib.parse.urlencode({
            'secret': turnstile_secret_key,
            'response': turnstile_response,
            'remoteip': request.META.get('REMOTE_ADDR')
        }).encode('utf-8')
        
        try:
            req = urllib.request.Request(
                verify_url, 
                data=post_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            if not result.get('success'):
                messages.error(request, "CAPTCHA verification failed. Please prove you are not a robot.")
                return redirect('index')
        except Exception as e:
            # Fallback strategy: fail open in case of network issues
            print(f"Turnstile verification exception: {e}")

        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        if not name or not email or not message_text:
            messages.error(request, "Please fill in all required fields.")
            return redirect('index')
            
        # Profanity filter
        if profanity.contains_profanity(name) or \
           profanity.contains_profanity(subject or '') or \
           profanity.contains_profanity(message_text) or \
           profanity.contains_profanity(email):
            messages.error(request, "Your message contains inappropriate content and could not be sent.")
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

def sitemap_view(request):
    from django.http import HttpResponse
    db = get_db()
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    # Fetch dynamic articles & projects
    blogs = db.blogs.find({'is_published': True}, {'slug': 1, 'created_at': 1})
    projects = db.projects.find({}, {'slug': 1})
    
    xml_items = []
    
    # Homepage
    xml_items.append(f"  <url>\n    <loc>{base_url}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>")
    
    # Blog Index
    xml_items.append(f"  <url>\n    <loc>{base_url}/blogs/</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>")
    
    # Blogs
    for b in blogs:
        slug = b.get('slug')
        if slug:
            lastmod = ""
            created = b.get('created_at')
            if isinstance(created, datetime):
                lastmod = f"\n    <lastmod>{created.strftime('%Y-%m-%d')}</lastmod>"
            xml_items.append(f"  <url>\n    <loc>{base_url}/blog/{slug}/</loc>{lastmod}\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>")
            
    # Projects
    for p in projects:
        slug = p.get('slug')
        if slug:
            xml_items.append(f"  <url>\n    <loc>{base_url}/project/{slug}/</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>")
            
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' \
                  + '\n'.join(xml_items) + '\n' \
                  '</urlset>'
                  
    return HttpResponse(xml_content, content_type='application/xml')

def rss_feed_view(request):
    from django.http import HttpResponse
    from django.utils.feedgenerator import rfc2822_date
    from django.utils.html import strip_tags
    from xml.sax.saxutils import escape
    
    db = get_db()
    base_url = request.build_absolute_uri('/').rstrip('/')
    profile = db.profile.find_one() or {}
    author_name = profile.get('name', 'Dhruv Bhirud')
    
    blogs = list(db.blogs.find({'is_published': True}).sort('created_at', -1).limit(20))
    
    rss_items = []
    for b in blogs:
        slug = b.get('slug')
        title = escape(b.get('title', ''))
        desc = escape(strip_tags(b.get('content', ''))[:300] + '...')
        link = f"{base_url}/blog/{slug}/"
        
        pub_date = ""
        created = b.get('created_at')
        if isinstance(created, datetime):
            pub_date = f"\n      <pubDate>{rfc2822_date(created)}</pubDate>"
            
        rss_items.append(
            f"    <item>\n"
            f"      <title>{title}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <description>{desc}</description>\n"
            f"      <guid>{link}</guid>{pub_date}\n"
            f"    </item>"
        )
        
    rss_content = '<?xml version="1.0" encoding="utf-8"?>\n' \
                  '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n' \
                  '  <channel>\n' \
                  f'    <title>{author_name}\'s Blog</title>\n' \
                  f'    <link>{base_url}/blogs/</link>\n' \
                  f'    <description>Recent articles and thoughts from {author_name}</description>\n' \
                  f'    <atom:link href="{base_url}/feed/" rel="self" type="application/rss+xml" />\n' \
                  + '\n'.join(rss_items) + '\n' \
                  '  </channel>\n' \
                  '</rss>'
                  
    return HttpResponse(rss_content, content_type='application/rss+xml')

def robots_txt_view(request):
    from django.http import HttpResponse
    base_url = request.build_absolute_uri('/').rstrip('/')
    content = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Allow: /blogs/\n"
        "Allow: /project/\n"
        "Allow: /\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return HttpResponse(content, content_type='text/plain')

def handler404(request, exception=None):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def endorse_skill(request, skill_id):
    from django.http import JsonResponse
    from django.core.cache import cache
    from bson import ObjectId
    from better_profanity import profanity
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
        
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
        
    name = data.get('name', '').strip()
    comment = data.get('comment', '').strip()
    
    if not name:
        return JsonResponse({'error': 'Name is required.'}, status=400)
        
    if len(name) > 50:
        return JsonResponse({'error': 'Name must be 50 characters or less.'}, status=400)
        
    if len(comment) > 200:
        return JsonResponse({'error': 'Comment must be 200 characters or less.'}, status=400)
        
    if profanity.contains_profanity(name) or profanity.contains_profanity(comment):
        return JsonResponse({'error': 'Inappropriate content detected.'}, status=400)
        
    # Rate limiting: 1 endorsement per IP per skill every 24 hours
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
        
    cache_key = f"endorse_{ip}_{skill_id}"
    if cache.get(cache_key):
        return JsonResponse({'error': 'You have already endorsed this skill recently. Please try again tomorrow.'}, status=429)
        
    db = get_db()
    skill = db.skills.find_one({'_id': ObjectId(skill_id)})
    if not skill:
        return JsonResponse({'error': 'Skill not found.'}, status=404)
        
    endorsement_id = str(ObjectId())
    new_endorser = {
        'id': endorsement_id,
        'name': name,
        'comment': comment,
        'created_at': datetime.now(),
        'approved': False
    }
    
    db.skills.update_one(
        {'_id': ObjectId(skill_id)},
        {
            '$push': {'endorsers': new_endorser}
        }
    )
    
    cache.set(cache_key, True, 86400)
    
    return JsonResponse({
        'status': 'pending',
        'message': 'Thank you! Your endorsement has been submitted for moderation.'
    })