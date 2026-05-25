from django.test import SimpleTestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from datetime import datetime
from bson import ObjectId
import json

# --- MongoDB Mock Classes ---

class MockCursor:
    def __init__(self, data):
        self.data = list(data)

    def sort(self, *args, **kwargs):
        try:
            if args:
                sort_key = args[0]
                if isinstance(sort_key, list):
                    # Multi-key sorting, e.g. [('is_featured', -1), ('order', 1)]
                    def get_sort_tuple(item):
                        vals = []
                        for k, order in sort_key:
                            val = item.get(k, 0)
                            if order == -1:
                                if isinstance(val, bool):
                                    val = 0 if val else 1
                                elif isinstance(val, (int, float)):
                                    val = -val
                            vals.append(val)
                        return tuple(vals)
                    self.data.sort(key=get_sort_tuple)
                elif isinstance(sort_key, str):
                    direction = args[1] if len(args) > 1 else 1
                    reverse = (direction == -1)
                    self.data.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)
        except Exception:
            pass
        return self

    def skip(self, count):
        self.data = self.data[count:]
        return self

    def limit(self, count):
        self.data = self.data[:count]
        return self

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __len__(self):
        return len(self.data)


class MockCollection:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self.documents = []

    def find(self, filter=None, projection=None):
        if not filter:
            return MockCursor(self.documents)

        filtered_docs = []
        import re
        for doc in self.documents:
            match = True
            for k, v in filter.items():
                if k == '$or':
                    or_matches = False
                    for sub_filter in v:
                        sub_match = True
                        for sk, sv in sub_filter.items():
                            val = doc.get(sk, '')
                            if isinstance(sv, dict) and '$regex' in sv:
                                pattern = sv['$regex']
                                flags = re.IGNORECASE if 'i' in sv.get('$options', '') else 0
                                if not re.search(pattern, str(val), flags):
                                    sub_match = False
                                    break
                            else:
                                if val != sv:
                                    sub_match = False
                                    break
                        if sub_match:
                            or_matches = True
                            break
                    if not or_matches:
                        match = False
                        break
                elif k == 'tags':
                    if isinstance(v, dict):
                        if '$regex' in v:
                            pattern = v['$regex']
                            flags = re.IGNORECASE if 'i' in v.get('$options', '') else 0
                            if not re.search(pattern, str(doc.get('tags', '')), flags):
                                match = False
                                break
                        elif '$exists' in v and '$ne' in v:
                            if 'tags' not in doc or doc.get('tags') == v['$ne']:
                                match = False
                                break
                    else:
                        if doc.get('tags') != v:
                            match = False
                            break
                else:
                    if k == '_id':
                        if str(doc.get('_id')) != str(v):
                            match = False
                            break
                    else:
                        if doc.get(k) != v:
                            match = False
                            break
            if match:
                filtered_docs.append(doc)

        return MockCursor(filtered_docs)

    def find_one(self, filter=None, *args, **kwargs):
        cursor = self.find(filter)
        sort_arg = kwargs.get('sort')
        if sort_arg:
            cursor.sort(sort_arg)
        elif len(args) > 0 and (isinstance(args[0], list) or isinstance(args[0], tuple)):
            cursor.sort(args[0])

        if len(cursor.data) > 0:
            return cursor.data[0]
        return None

    def count_documents(self, filter, *args, **kwargs):
        return len(self.find(filter).data)

    def update_one(self, filter, update, *args, **kwargs):
        doc = self.find_one(filter)
        upsert = kwargs.get('upsert', False)
        if not doc and upsert:
            doc = {}
            if '_id' not in doc:
                doc['_id'] = ObjectId()
            # If type is specified in filter, preserve it
            if filter and 'type' in filter:
                doc['type'] = filter['type']
            self.documents.append(doc)

        if doc:
            if '$inc' in update:
                for k, v in update['$inc'].items():
                    doc[k] = doc.get(k, 0) + v
            if '$set' in update:
                for k, v in update['$set'].items():
                    doc[k] = v
        return MagicMock()

    def insert_one(self, document, *args, **kwargs):
        if '_id' not in document:
            document['_id'] = ObjectId()
        self.documents.append(document)
        return MagicMock(inserted_id=document['_id'])

    def delete_many(self, filter, *args, **kwargs):
        if '_id' in filter and '$in' in filter['_id']:
            ids_to_delete = filter['_id']['$in']
            self.documents = [doc for doc in self.documents if str(doc.get('_id')) not in [str(x) for x in ids_to_delete]]
        return MagicMock()

    def delete_one(self, filter, *args, **kwargs):
        doc = self.find_one(filter)
        if doc:
            self.documents.remove(doc)
        return MagicMock()

    def distinct(self, key, filter=None, *args, **kwargs):
        values = set()
        for doc in self.find(filter):
            val = doc.get(key)
            if val is not None:
                values.add(val)
        return list(values)


class MockDB:
    def __init__(self):
        self.projects = MockCollection('projects', self)
        self.skills = MockCollection('skills', self)
        self.blogs = MockCollection('blogs', self)
        self.profile = MockCollection('profile', self)
        self.settings = MockCollection('settings', self)
        self.messages = MockCollection('messages', self)

    def __getitem__(self, name):
        return getattr(self, name)


# --- Base Test Case ---

class BaseViewTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.mock_db = MockDB()
        
        # Patch views.get_db
        self.get_db_patcher = patch('main.views.get_db', return_value=self.mock_db)
        self.mock_get_db = self.get_db_patcher.start()

        # Patch admin_views.get_db
        self.admin_get_db_patcher = patch('main.admin_views.get_db', return_value=self.mock_db)
        self.mock_admin_get_db = self.admin_get_db_patcher.start()

        # Patch Cloudinary
        self.cloudinary_patcher = patch('cloudinary.uploader.upload', return_value={'secure_url': 'http://example.com/uploaded.jpg'})
        self.mock_cloudinary = self.cloudinary_patcher.start()
        
        self.setup_default_data()

    def tearDown(self):
        self.get_db_patcher.stop()
        self.admin_get_db_patcher.stop()
        self.cloudinary_patcher.stop()
        super().tearDown()

    def setup_default_data(self):
        # Profile Data
        self.mock_db.profile.documents = [
            {
                '_id': ObjectId(),
                'name': 'Dhruv Bhirud',
                'title': 'Software Developer',
                'bio': 'Passionate developer.',
                'email': 'bhiruddhruv@gmail.com',
                'github': 'https://github.com/dhruvbhirud',
                'linkedin': 'https://linkedin.com/in/dhruvbhirud',
                'resume_url': 'http://example.com/resume.pdf',
                'views': 10
            }
        ]
        
        # General & SMTP Settings
        self.mock_db.settings.documents = [
            {
                '_id': ObjectId(),
                'type': 'general',
                'turnstile_site_key': 'test-site-key',
                'turnstile_secret_key': 'test-secret-key',
                'max_messages': 5
            },
            {
                '_id': ObjectId(),
                'type': 'smtp',
                'host': 'smtp.example.com',
                'port': 587,
                'user': 'smtp_user',
                'password': 'smtp_password',
                'from_email': 'no-reply@example.com',
                'use_tls': True
            }
        ]
        
        # Skills
        self.mock_db.skills.documents = [
            {'_id': ObjectId(), 'name': 'Python', 'category': 'Languages', 'order': 1},
            {'_id': ObjectId(), 'name': 'JavaScript', 'category': 'Languages', 'order': 2},
            {'_id': ObjectId(), 'name': 'Django', 'category': 'Frameworks', 'order': 1},
        ]
        
        # Projects
        self.mock_db.projects.documents = [
            {
                '_id': ObjectId(),
                'title': 'Portfolio Website',
                'slug': 'portfolio-website',
                'description': 'This project.',
                'tech': 'Python, Django, MongoDB',
                'is_featured': True,
                'order': 1,
                'views': 15
            },
            {
                '_id': ObjectId(),
                'title': 'Other Project',
                'slug': 'other-project',
                'description': 'Some other project.',
                'tech': 'JavaScript, HTML',
                'is_featured': False,
                'order': 2,
                'views': 5
            }
        ]
        
        # Blogs
        self.mock_db.blogs.documents = [
            {
                '_id': ObjectId(),
                'title': 'Intro to Django',
                'slug': 'intro-to-django',
                'content': 'This is a long content block to test read time. Word ' * 50,
                'tags': 'django, python',
                'is_published': True,
                'created_at': datetime(2026, 5, 20),
                'views': 2
            },
            {
                '_id': ObjectId(),
                'title': 'Intro to MongoDB',
                'slug': 'intro-to-mongodb',
                'content': 'MongoDB is a document store.',
                'tags': 'mongodb, database',
                'is_published': True,
                'created_at': datetime(2026, 5, 22),
                'views': 4
            },
            {
                '_id': ObjectId(),
                'title': 'Draft Post',
                'slug': 'draft-post',
                'content': 'Draft post content.',
                'tags': 'misc',
                'is_published': False,
                'created_at': datetime(2026, 5, 25),
                'views': 0
            }
        ]


# --- Admin Authenticated Base Case ---

class AdminBaseViewTestCase(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        from django.conf import settings
        session = self.client.session
        session['admin_logged_in'] = True
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key


# ======================================================================
# --- Main Frontend Tests ---
# ======================================================================

class HomepageTests(BaseViewTestCase):
    def test_homepage_renders_successfully(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/index.html')
        self.assertIn('projects', response.context)
        self.assertIn('grouped_skills', response.context)
        self.assertIn('blogs', response.context)
        
        projects = response.context['projects']
        self.assertEqual(len(projects), 2)
        self.assertTrue(projects[0]['is_featured'])

        profile = self.mock_db.profile.find_one()
        self.assertEqual(profile['views'], 11)


class ProjectDetailTests(BaseViewTestCase):
    def test_project_detail_view_renders(self):
        response = self.client.get(reverse('project_detail', kwargs={'project_slug': 'portfolio-website'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/project_detail.html')
        self.assertEqual(response.context['project']['slug'], 'portfolio-website')
        
        project = self.mock_db.projects.find_one({'slug': 'portfolio-website'})
        self.assertEqual(project['views'], 16)

    def test_project_detail_missing_project(self):
        response = self.client.get(reverse('project_detail', kwargs={'project_slug': 'non-existent'}))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['project'])


class BlogIndexTests(BaseViewTestCase):
    def test_blog_index_renders(self):
        response = self.client.get(reverse('blog_index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/blog_index.html')
        self.assertEqual(len(response.context['blogs']), 2)

    def test_blog_index_search(self):
        response = self.client.get(reverse('blog_index') + '?q=Django')
        self.assertEqual(response.status_code, 200)
        blogs = response.context['blogs']
        self.assertEqual(len(blogs), 1)
        self.assertEqual(blogs[0]['slug'], 'intro-to-django')

    def test_blog_index_tag_filter(self):
        response = self.client.get(reverse('blog_index') + '?tag=python')
        self.assertEqual(response.status_code, 200)
        blogs = response.context['blogs']
        self.assertEqual(len(blogs), 1)
        self.assertEqual(blogs[0]['slug'], 'intro-to-django')


class BlogDetailTests(BaseViewTestCase):
    def test_blog_detail_view_renders(self):
        response = self.client.get(reverse('blog_detail', kwargs={'blog_slug': 'intro-to-django'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/blog_detail.html')
        self.assertEqual(response.context['blog']['slug'], 'intro-to-django')
        self.assertEqual(response.context['blog']['read_time'], 3)
        
        blog = self.mock_db.blogs.find_one({'slug': 'intro-to-django'})
        self.assertEqual(blog['views'], 3)


class RobotsTxtTests(SimpleTestCase):
    def test_robots_txt_status_and_content_type(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')

    def test_robots_txt_content_directives(self):
        response = self.client.get(reverse('robots_txt'))
        content = response.content.decode('utf-8')
        
        self.assertIn("User-agent: *", content)
        self.assertIn("Disallow: /admin/", content)
        self.assertIn("Allow: /blogs/", content)
        self.assertIn("Allow: /project/", content)
        self.assertIn("Allow: /", content)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", content)


class SitemapTests(BaseViewTestCase):
    def test_sitemap_xml_renders(self):
        response = self.client.get(reverse('sitemap'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        content = response.content.decode('utf-8')
        
        self.assertIn('<loc>http://testserver/</loc>', content)
        self.assertIn('<loc>http://testserver/blogs/</loc>', content)
        self.assertIn('<loc>http://testserver/blog/intro-to-django/</loc>', content)
        self.assertIn('<loc>http://testserver/project/portfolio-website/</loc>', content)


class RssFeedTests(BaseViewTestCase):
    def test_rss_feed_renders(self):
        response = self.client.get(reverse('rss_feed'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/rss+xml')
        content = response.content.decode('utf-8')
        
        self.assertIn("<title>Dhruv Bhirud's Blog</title>", content)
        self.assertIn("<link>http://testserver/blogs/</link>", content)
        self.assertIn("<title>Intro to Django</title>", content)
        self.assertIn("<title>Intro to MongoDB</title>", content)


class ContactSubmissionTests(BaseViewTestCase):
    def test_submit_contact_get_redirects(self):
        response = self.client.get(reverse('submit_contact'))
        self.assertRedirects(response, reverse('index'))

    @patch('urllib.request.urlopen')
    @patch('django.core.mail.EmailMessage.send')
    def test_submit_contact_success(self, mock_email_send, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        post_data = {
            'cf-turnstile-response': 'valid-captcha-response',
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Hello',
            'message': 'This is a test message.'
        }
        
        response = self.client.post(reverse('submit_contact'), post_data)
        self.assertRedirects(response, reverse('index'))
        
        messages_in_db = self.mock_db.messages.documents
        self.assertEqual(len(messages_in_db), 1)
        self.assertEqual(messages_in_db[0]['name'], 'John Doe')
        self.assertEqual(messages_in_db[0]['message'], 'This is a test message.')
        self.assertTrue(mock_email_send.called)

    @patch('urllib.request.urlopen')
    def test_submit_contact_missing_fields(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        post_data = {
            'cf-turnstile-response': 'valid-captcha-response',
            'name': '',
            'email': 'john@example.com',
            'subject': 'Hello',
            'message': 'No name'
        }
        
        response = self.client.post(reverse('submit_contact'), post_data)
        self.assertRedirects(response, reverse('index'))
        self.assertEqual(len(self.mock_db.messages.documents), 0)

    @patch('urllib.request.urlopen')
    def test_submit_contact_profanity_filtering(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        post_data = {
            'cf-turnstile-response': 'valid-captcha-response',
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Hello',
            'message': 'This is badword text.'
        }
        
        with patch('better_profanity.profanity.contains_profanity', return_value=True):
            response = self.client.post(reverse('submit_contact'), post_data)
            
        self.assertRedirects(response, reverse('index'))
        self.assertEqual(len(self.mock_db.messages.documents), 0)

    @patch('urllib.request.urlopen')
    @patch('django.core.mail.EmailMessage.send')
    def test_submit_contact_storage_limit_enforced(self, mock_email_send, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        for i in range(5):
            self.mock_db.messages.insert_one({
                '_id': ObjectId(),
                'name': f'User {i}',
                'email': f'user{i}@example.com',
                'subject': 'Pre-fill',
                'message': f'Message {i}',
                'created_at': datetime(2026, 5, i + 1)
            })

        post_data = {
            'cf-turnstile-response': 'valid-captcha-response',
            'name': 'New User',
            'email': 'new@example.com',
            'subject': 'Limit Check',
            'message': 'I am the sixth message.'
        }
        
        response = self.client.post(reverse('submit_contact'), post_data)
        self.assertRedirects(response, reverse('index'))
        
        messages_in_db = self.mock_db.messages.documents
        self.assertEqual(len(messages_in_db), 5)
        names = [m['name'] for m in messages_in_db]
        self.assertNotIn('User 0', names)
        self.assertIn('New User', names)


# ======================================================================
# --- Admin Authentication & Access Tests ---
# ======================================================================

class AdminAuthTests(BaseViewTestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/login.html')

    def test_login_success(self):
        # We prefill settings for admin_auth with custom hashed password
        from django.contrib.auth.hashers import make_password
        self.mock_db.settings.insert_one({
            'type': 'admin_auth',
            'password_hash': make_password('mypassword')
        })

        response = self.client.post(reverse('admin_login'), {'password': 'mypassword'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertTrue(self.client.session.get('admin_logged_in'))

    def test_login_incorrect_password(self):
        from django.contrib.auth.hashers import make_password
        self.mock_db.settings.insert_one({
            'type': 'admin_auth',
            'password_hash': make_password('mypassword')
        })

        response = self.client.post(reverse('admin_login'), {'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid password")
        self.assertFalse(self.client.session.get('admin_logged_in'))

    def test_login_fallback_password_first_time(self):
        # Ensure there is NO admin_auth setting initially
        self.mock_db.settings.documents = []
        from django.conf import settings
        fallback_password = getattr(settings, 'ADMIN_PASSWORD', 'admin123')

        response = self.client.post(reverse('admin_login'), {'password': fallback_password})
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertTrue(self.client.session.get('admin_logged_in'))

        # Verify password hash was created and saved
        auth_setting = self.mock_db.settings.find_one({'type': 'admin_auth'})
        self.assertIsNotNone(auth_setting)
        self.assertTrue(auth_setting.get('password_hash'))

    def test_logout(self):
        session = self.client.session
        session['admin_logged_in'] = True
        session.save()

        response = self.client.get(reverse('admin_logout'))
        self.assertRedirects(response, reverse('admin_login'))
        self.assertFalse(self.client.session.get('admin_logged_in'))


class AdminDecoratorTests(BaseViewTestCase):
    def test_protected_endpoints_redirect_when_unauthenticated(self):
        endpoints = [
            ('admin_dashboard', {}),
            ('admin_profile', {}),
            ('admin_blogs', {}),
            ('admin_blog_add', {}),
            ('admin_skills', {}),
            ('admin_projects', {}),
            ('admin_messages', {}),
            ('admin_settings', {}),
        ]
        for name, kwargs in endpoints:
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertRedirects(response, reverse('admin_login'))


# ======================================================================
# --- Admin Dashboard View Tests ---
# ======================================================================

class AdminDashboardTests(AdminBaseViewTestCase):
    def test_dashboard_renders_stats(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/dashboard.html')
        self.assertEqual(response.context['project_count'], 2)
        self.assertEqual(response.context['blog_count'], 3)
        self.assertEqual(response.context['published_blog_count'], 2)
        self.assertEqual(response.context['skill_count'], 3)
        self.assertEqual(response.context['homepage_views'], 10)
        # Blogs views sum: 2 + 4 + 0 = 6
        self.assertEqual(response.context['total_blog_views'], 6)
        # Projects views sum: 15 + 5 = 20
        self.assertEqual(response.context['total_project_views'], 20)
        # Total views: 10 + 6 + 20 = 36
        self.assertEqual(response.context['total_views'], 36)

        # Popular checks
        self.assertEqual(response.context['popular_blogs'][0]['slug'], 'intro-to-mongodb') # view count 4
        self.assertEqual(response.context['popular_projects'][0]['slug'], 'portfolio-website') # view count 15


# ======================================================================
# --- Admin Profile Tests ---
# ======================================================================

class AdminProfileTests(AdminBaseViewTestCase):
    def test_edit_profile_get(self):
        response = self.client.get(reverse('admin_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/edit_profile.html')
        self.assertEqual(response.context['profile']['name'], 'Dhruv Bhirud')

    def test_edit_profile_post_text_only(self):
        post_data = {
            'name': 'Dhruv New Name',
            'title': 'Senior Developer',
            'bio': 'New bio info.',
            'email': 'dhruvbhirud@example.com',
            'github': 'https://github.com/dhruvnew',
            'linkedin': 'https://linkedin.com/in/dhruvnew',
        }
        response = self.client.post(reverse('admin_profile'), post_data)
        self.assertRedirects(response, reverse('admin_profile'))

        profile = self.mock_db.profile.find_one()
        self.assertEqual(profile['name'], 'Dhruv New Name')
        self.assertEqual(profile['title'], 'Senior Developer')
        # Check that it kept the old resume_url
        self.assertEqual(profile['resume_url'], 'http://example.com/resume.pdf')

    def test_edit_profile_post_with_resume_file(self):
        resume_file = SimpleUploadedFile('resume.pdf', b'sample pdf content', content_type='application/pdf')
        post_data = {
            'name': 'Dhruv Bhirud',
            'title': 'Software Developer',
            'bio': 'Passionate developer.',
            'email': 'bhiruddhruv@gmail.com',
            'github': 'https://github.com/dhruvbhirud',
            'linkedin': 'https://linkedin.com/in/dhruvbhirud',
            'resume': resume_file
        }
        response = self.client.post(reverse('admin_profile'), post_data)
        self.assertRedirects(response, reverse('admin_profile'))

        # Check Cloudinary upload was called
        self.assertTrue(self.mock_cloudinary.called)
        
        # Verify resume_url was updated to the mocked cloudinary url
        profile = self.mock_db.profile.find_one()
        self.assertEqual(profile['resume_url'], 'http://example.com/uploaded.jpg')


# ======================================================================
# --- Admin Blog Tests ---
# ======================================================================

class AdminBlogTests(AdminBaseViewTestCase):
    def test_list_blogs(self):
        response = self.client.get(reverse('admin_blogs'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/list_blogs.html')
        self.assertEqual(len(response.context['blogs']), 3)

    def test_edit_blog_get_new(self):
        response = self.client.get(reverse('admin_blog_add'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/edit_blog.html')
        self.assertEqual(response.context['blog'], {})

    def test_edit_blog_get_existing(self):
        blog = self.mock_db.blogs.find_one({'slug': 'intro-to-django'})
        response = self.client.get(reverse('admin_blog_edit', kwargs={'blog_id': str(blog['_id'])}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/edit_blog.html')
        self.assertEqual(response.context['blog']['title'], 'Intro to Django')

    def test_edit_blog_post_new(self):
        image_file = SimpleUploadedFile('blog.jpg', b'image data', content_type='image/jpeg')
        post_data = {
            'title': 'New Blog Title',
            'content': 'This is new blog content.',
            'tags': 'new, test',
            'is_published': 'on',
            'image': image_file
        }
        response = self.client.post(reverse('admin_blog_add'), post_data)
        self.assertRedirects(response, reverse('admin_blogs'))

        # Verify added to DB
        blog = self.mock_db.blogs.find_one({'slug': 'new-blog-title'})
        self.assertIsNotNone(blog)
        self.assertEqual(blog['content'], 'This is new blog content.')
        self.assertEqual(blog['image_url'], 'http://example.com/uploaded.jpg')
        self.assertTrue(blog['is_published'])
        self.assertIsInstance(blog['created_at'], datetime)

    def test_edit_blog_post_existing(self):
        blog = self.mock_db.blogs.find_one({'slug': 'intro-to-django'})
        post_data = {
            'title': 'Updated Title',
            'content': 'Updated content.',
            'tags': 'updated',
            # is_published is omitted, should be false
        }
        response = self.client.post(reverse('admin_blog_edit', kwargs={'blog_id': str(blog['_id'])}), post_data)
        self.assertRedirects(response, reverse('admin_blogs'))

        updated_blog = self.mock_db.blogs.find_one({'_id': blog['_id']})
        self.assertEqual(updated_blog['title'], 'Updated Title')
        self.assertEqual(updated_blog['slug'], 'updated-title')
        self.assertEqual(updated_blog['content'], 'Updated content.')
        self.assertFalse(updated_blog['is_published'])

    def test_delete_blog_post(self):
        blog = self.mock_db.blogs.find_one({'slug': 'intro-to-django'})
        response = self.client.post(reverse('admin_blog_delete', kwargs={'blog_id': str(blog['_id'])}))
        self.assertRedirects(response, reverse('admin_blogs'))
        
        deleted_blog = self.mock_db.blogs.find_one({'_id': blog['_id']})
        self.assertIsNone(deleted_blog)


# ======================================================================
# --- Admin Skill Tests ---
# ======================================================================

class AdminSkillTests(AdminBaseViewTestCase):
    def test_manage_skills_get_and_auto_migration(self):
        # Place a skill without category or order to test migration
        self.mock_db.skills.documents.append({
            '_id': ObjectId(),
            'name': 'Unmigrated Skill'
        })

        response = self.client.get(reverse('admin_skills'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/manage_skills.html')
        self.assertEqual(len(response.context['skills']), 4)
        
        # Verify migrated in DB
        migrated_skill = self.mock_db.skills.find_one({'name': 'Unmigrated Skill'})
        self.assertEqual(migrated_skill['category'], 'Other')
        self.assertIsNotNone(migrated_skill['order'])

    def test_manage_skills_post_new(self):
        icon_file = SimpleUploadedFile('icon.png', b'icon data', content_type='image/png')
        post_data = {
            'name': 'New Skill',
            'category': 'Libraries',
            'icon_class': 'fa-react',
            'custom_icon': icon_file
        }
        response = self.client.post(reverse('admin_skills'), post_data)
        self.assertRedirects(response, reverse('admin_skills'))

        skill = self.mock_db.skills.find_one({'name': 'New Skill'})
        self.assertIsNotNone(skill)
        self.assertEqual(skill['category'], 'Libraries')
        self.assertEqual(skill['icon_class'], 'fa-react')
        self.assertEqual(skill['image_url'], 'http://example.com/uploaded.jpg')
        # Order should increment based on max order
        self.assertEqual(skill['order'], 3)

    def test_edit_skill_get(self):
        skill = self.mock_db.skills.find_one({'name': 'Python'})
        response = self.client.get(reverse('admin_skill_edit', kwargs={'skill_id': str(skill['_id'])}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/edit_skill.html')
        self.assertEqual(response.context['skill']['name'], 'Python')

    def test_edit_skill_post(self):
        skill = self.mock_db.skills.find_one({'name': 'Python'})
        post_data = {
            'name': 'Python 3',
            'category': 'Backend Languages',
            'icon_class': 'fa-python-3'
        }
        response = self.client.post(reverse('admin_skill_edit', kwargs={'skill_id': str(skill['_id'])}), post_data)
        self.assertRedirects(response, reverse('admin_skills'))

        updated_skill = self.mock_db.skills.find_one({'_id': skill['_id']})
        self.assertEqual(updated_skill['name'], 'Python 3')
        self.assertEqual(updated_skill['category'], 'Backend Languages')
        self.assertEqual(updated_skill['icon_class'], 'fa-python-3')

    def test_delete_skill_post(self):
        skill = self.mock_db.skills.find_one({'name': 'Python'})
        response = self.client.post(reverse('admin_skill_delete', kwargs={'skill_id': str(skill['_id'])}))
        self.assertRedirects(response, reverse('admin_skills'))

        deleted_skill = self.mock_db.skills.find_one({'_id': skill['_id']})
        self.assertIsNone(deleted_skill)

    def test_reorder_skills_post(self):
        skills = self.mock_db.skills.documents
        # Reorder IDs list
        ids_order = [str(skills[2]['_id']), str(skills[0]['_id']), str(skills[1]['_id'])]
        
        response = self.client.post(
            reverse('admin_skills_reorder'),
            json.dumps(ids_order),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})

        # Verify updated orders
        self.assertEqual(self.mock_db.skills.find_one({'_id': skills[2]['_id']})['order'], 0)
        self.assertEqual(self.mock_db.skills.find_one({'_id': skills[0]['_id']})['order'], 1)
        self.assertEqual(self.mock_db.skills.find_one({'_id': skills[1]['_id']})['order'], 2)


# ======================================================================
# --- Admin Project Tests ---
# ======================================================================

class AdminProjectTests(AdminBaseViewTestCase):
    def test_list_projects(self):
        response = self.client.get(reverse('admin_projects'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/list_projects.html')
        self.assertEqual(len(response.context['projects']), 2)

    def test_edit_project_get_new(self):
        response = self.client.get(reverse('admin_project_add'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/edit_project.html')
        self.assertEqual(response.context['project'], {})

    def test_edit_project_post_new(self):
        image_file = SimpleUploadedFile('project.png', b'project image data', content_type='image/png')
        post_data = {
            'title': 'Brand New Project',
            'description': 'Short description.',
            'tech': 'HTML, CSS',
            'github_url': 'http://github.com/newproj',
            'live_url': 'http://newproj.com',
            'long_description': 'Detailed breakdown.',
            'order': 3,
            'is_featured': 'on',
            'image': image_file
        }
        response = self.client.post(reverse('admin_project_add'), post_data)
        self.assertRedirects(response, reverse('admin_projects'))

        project = self.mock_db.projects.find_one({'slug': 'brand-new-project'})
        self.assertIsNotNone(project)
        self.assertEqual(project['tech'], 'HTML, CSS')
        self.assertEqual(project['image_url'], 'http://example.com/uploaded.jpg')
        self.assertTrue(project['is_featured'])

    def test_edit_project_post_existing(self):
        project = self.mock_db.projects.find_one({'slug': 'portfolio-website'})
        post_data = {
            'title': 'Portfolio Updated',
            'description': 'Updated short desc.',
            'tech': 'Django, PyMongo',
            'github_url': '',
            'live_url': '',
            'long_description': 'Updated detailed info.',
            'order': 1,
            # 'is_featured' is omitted
        }
        response = self.client.post(reverse('admin_project_edit', kwargs={'project_id': str(project['_id'])}), post_data)
        self.assertRedirects(response, reverse('admin_projects'))

        updated_project = self.mock_db.projects.find_one({'_id': project['_id']})
        self.assertEqual(updated_project['title'], 'Portfolio Updated')
        self.assertEqual(updated_project['slug'], 'portfolio-updated')
        self.assertEqual(updated_project['tech'], 'Django, PyMongo')
        self.assertFalse(updated_project['is_featured'])

    def test_delete_project_post(self):
        project = self.mock_db.projects.find_one({'slug': 'portfolio-website'})
        response = self.client.post(reverse('admin_project_delete', kwargs={'project_id': str(project['_id'])}))
        self.assertRedirects(response, reverse('admin_projects'))

        deleted_project = self.mock_db.projects.find_one({'_id': project['_id']})
        self.assertIsNone(deleted_project)


# ======================================================================
# --- Admin Messages Tests ---
# ======================================================================

class AdminMessageTests(AdminBaseViewTestCase):
    def setUp(self):
        super().setUp()
        # Insert a default message
        self.msg_id = ObjectId()
        self.mock_db.messages.documents = [
            {
                '_id': self.msg_id,
                'name': 'Client User',
                'email': 'client@example.com',
                'subject': 'Inquiry',
                'message': 'Hello there.',
                'created_at': datetime.now(),
                'is_read': False
            }
        ]

    def test_list_messages(self):
        response = self.client.get(reverse('admin_messages'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/messages_list.html')
        self.assertEqual(len(response.context['messages']), 1)

    def test_view_message_marks_as_read(self):
        response = self.client.get(reverse('admin_view_message', kwargs={'message_id': str(self.msg_id)}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/view_message.html')
        
        # Should now be read in DB
        msg = self.mock_db.messages.find_one({'_id': self.msg_id})
        self.assertTrue(msg['is_read'])

    def test_delete_message_post(self):
        response = self.client.post(reverse('admin_delete_message', kwargs={'message_id': str(self.msg_id)}))
        self.assertRedirects(response, reverse('admin_messages'))

        msg = self.mock_db.messages.find_one({'_id': self.msg_id})
        self.assertIsNone(msg)


# ======================================================================
# --- Admin Settings Tests ---
# ======================================================================

class AdminSettingsTests(AdminBaseViewTestCase):
    def test_admin_settings_get(self):
        response = self.client.get(reverse('admin_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/admin/settings.html')
        self.assertEqual(response.context['general']['max_messages'], 5)

    def test_admin_settings_update_config(self):
        post_data = {
            'action': 'save_settings',
            'max_messages': 100,
            'turnstile_site_key': 'new-site-key',
            'turnstile_secret_key': 'new-secret-key',
            'host': 'smtp.gmail.com',
            'port': 465,
            'user': 'gmail_user',
            'password': 'gmail_password',
            'from_email': 'gmail@example.com',
            'use_tls': 'on'
        }
        response = self.client.post(reverse('admin_settings'), post_data)
        self.assertRedirects(response, reverse('admin_settings'))

        general = self.mock_db.settings.find_one({'type': 'general'})
        self.assertEqual(general['max_messages'], 100)
        self.assertEqual(general['turnstile_site_key'], 'new-site-key')

        smtp = self.mock_db.settings.find_one({'type': 'smtp'})
        self.assertEqual(smtp['host'], 'smtp.gmail.com')
        self.assertEqual(smtp['port'], 465)
        self.assertTrue(smtp['use_tls'])

    def test_admin_settings_change_password_success(self):
        from django.contrib.auth.hashers import make_password
        self.mock_db.settings.insert_one({
            'type': 'admin_auth',
            'password_hash': make_password('oldpwd')
        })

        post_data = {
            'action': 'change_password',
            'current_password': 'oldpwd',
            'new_password': 'newpwd',
            'confirm_password': 'newpwd'
        }
        response = self.client.post(reverse('admin_settings'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password updated successfully!")

        # Verify hashed password updated
        auth_doc = self.mock_db.settings.find_one({'type': 'admin_auth'})
        from django.contrib.auth.hashers import check_password
        self.assertTrue(check_password('newpwd', auth_doc['password_hash']))

    def test_admin_settings_change_password_incorrect_current(self):
        from django.contrib.auth.hashers import make_password
        self.mock_db.settings.insert_one({
            'type': 'admin_auth',
            'password_hash': make_password('oldpwd')
        })

        post_data = {
            'action': 'change_password',
            'current_password': 'wrongold',
            'new_password': 'newpwd',
            'confirm_password': 'newpwd'
        }
        response = self.client.post(reverse('admin_settings'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect current password.")

    def test_admin_settings_change_password_non_matching(self):
        from django.contrib.auth.hashers import make_password
        self.mock_db.settings.insert_one({
            'type': 'admin_auth',
            'password_hash': make_password('oldpwd')
        })

        post_data = {
            'action': 'change_password',
            'current_password': 'oldpwd',
            'new_password': 'newpwd1',
            'confirm_password': 'newpwd2'
        }
        response = self.client.post(reverse('admin_settings'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New passwords do not match.")

    @patch('django.core.mail.EmailMessage.send')
    def test_admin_settings_test_email_success(self, mock_email_send):
        post_data = {
            'action': 'test_email',
            'max_messages': 5,
            'host': 'smtp.example.com',
            'port': 587,
            'user': 'smtp_user',
            'password': 'smtp_password',
            'from_email': 'me@example.com',
            'use_tls': 'on'
        }
        response = self.client.post(reverse('admin_settings'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test email sent successfully!")
        self.assertTrue(mock_email_send.called)


# ======================================================================
# --- Admin Image Upload (TinyMCE) Endpoint Tests ---
# ======================================================================

class TinyMceUploadTests(AdminBaseViewTestCase):
    def test_upload_image_endpoint_success(self):
        dummy_file = SimpleUploadedFile('test.jpg', b'jpg data', content_type='image/jpeg')
        response = self.client.post(reverse('admin_upload_image'), {'file': dummy_file})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'location': 'http://example.com/uploaded.jpg'})

    def test_upload_image_endpoint_invalid_method(self):
        response = self.client.get(reverse('admin_upload_image'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid request'})

    def test_upload_image_endpoint_missing_file(self):
        response = self.client.post(reverse('admin_upload_image'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid request'})

    @patch('cloudinary.uploader.upload', side_effect=Exception("Cloudinary Error"))
    def test_upload_image_endpoint_cloudinary_failure(self, mock_upload):
        dummy_file = SimpleUploadedFile('test.jpg', b'jpg data', content_type='image/jpeg')
        response = self.client.post(reverse('admin_upload_image'), {'file': dummy_file})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'error': 'Cloudinary Error'})

from django.test import override_settings

@override_settings(DEBUG=False)
class ErrorPageTests(SimpleTestCase):
    def test_custom_404_page(self):
        response = self.client.get('/this-path-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertContains(response, '404', status_code=404)
        self.assertContains(response, 'Page Not Found', status_code=404)

    def test_custom_500_page(self):
        from main.views import handler500
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        response = handler500(request)
        self.assertEqual(response.status_code, 500)
        # 500 error page should contain 500 and Internal Server Error
        self.assertContains(response, '500', status_code=500)
        self.assertContains(response, 'Internal Server Error', status_code=500)
