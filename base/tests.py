from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from base.custom_filters import currency, phone_number

User = get_user_model()


class BaseAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="9876543210", password="password123", first_name="Test", last_name="Admin", is_staff=True
        )
        self.client = Client()

    def test_login_success(self):
        url = reverse("base:login")
        response = self.client.post(url, {"phone": "9876543210", "password": "password123"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("base:home"))

    def test_login_open_redirect_protection(self):
        url = reverse("base:login") + "?next=https://malicious-site.com"
        response = self.client.post(url, {"phone": "9876543210", "password": "password123"})
        # Must redirect safely to dashboard, not to malicious site
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("base:home"))

    def test_dashboard_view(self):
        self.client.login(username="9876543210", password="password123")
        url = reverse("base:home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revenue This Month")
        self.assertContains(response, "Vehicles In Workshop")
        self.assertContains(response, "Job Cards Today")

    def test_currency_filter(self):
        self.assertEqual(currency(1500), "1,500.00")
        self.assertEqual(currency("2500.50"), "2,500.50")
        self.assertEqual(currency(None), "0.00")
        self.assertEqual(currency(""), "0.00")

    def test_phone_number_filter(self):
        self.assertEqual(phone_number("9876543210"), "98765 43210")
        self.assertEqual(phone_number(None), "")

    def test_unauthenticated_user_redirected_by_middleware(self):
        """Unauthenticated requests to protected pages must redirect to login."""
        response = self.client.get(reverse("base:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_login_page_exempt_from_redirect(self):
        """Login page itself is exempt from the login requirement."""
        response = self.client.get(reverse("base:login"))
        self.assertEqual(response.status_code, 200)

    def test_session_meta_middleware_tracks_session(self):
        """SessionMetaMiddleware attaches IP and last_activity to the session."""
        self.client.login(username="9876543210", password="password123")
        response = self.client.get(reverse("base:home"))
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertIn("last_activity", session)
        self.assertIn("ip_address", session)
