from django.test import SimpleTestCase
from django.urls import reverse

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

