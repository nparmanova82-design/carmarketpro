import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from chat.models import Conversation
from listings.models import Brand, CarModel, Listing

User = get_user_model()
MEDIA = tempfile.mkdtemp()


def make_image(name="car.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class CarMarketFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.brand = Brand.objects.create(name="Toyota", slug="toyota")
        self.model = CarModel.objects.create(brand=self.brand, name="Camry")
        self.seller = User.objects.create_user("seller", "s@example.com", "StrongPass123!")
        self.buyer = User.objects.create_user("buyer", "b@example.com", "StrongPass123!")

    def auth(self, user):
        res = self.client.post("/api/auth/login/", {"username": user.username, "password": "StrongPass123!"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def create_listing(self, **extra):
        data = {"brand": self.brand.id, "car_model": self.model.id, "year": 2020, "price": "25000", "mileage": 40000}
        data.update(extra)
        return self.client.post("/api/listings/", data, format="multipart")

    def test_register_returns_tokens(self):
        res = self.client.post(
            "/api/auth/register/",
            {"username": "new", "email": "n@example.com", "password": "StrongPass123!", "password2": "StrongPass123!"},
        )
        self.assertEqual(res.status_code, 201)
        self.assertIn("access", res.data)

    def test_create_listing_with_multiple_photos(self):
        self.auth(self.seller)
        res = self.create_listing(images=[make_image("a.jpg"), make_image("b.jpg")])
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(len(res.data["photos"]), 2)
        self.assertEqual(res.data["title"], "Toyota Camry 2020")

    def test_filters(self):
        self.auth(self.seller)
        self.create_listing(price="10000", year=2015)
        self.create_listing(price="30000", year=2022)
        self.client.credentials()
        res = self.client.get("/api/listings/", {"price_max": 20000})
        self.assertEqual(res.data["count"], 1)
        res = self.client.get("/api/listings/", {"year_min": 2020, "search": "camry"})
        self.assertEqual(res.data["count"], 1)

    def test_only_owner_can_edit(self):
        self.auth(self.seller)
        listing_id = self.create_listing().data["id"]
        self.auth(self.buyer)
        res = self.client.patch(f"/api/listings/{listing_id}/", {"price": "1"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_favorite_comment_view_stats_and_chat(self):
        self.auth(self.seller)
        listing_id = self.create_listing().data["id"]

        self.auth(self.buyer)
        self.assertEqual(self.client.post(f"/api/listings/{listing_id}/favorite/").status_code, 201)
        self.assertEqual(self.client.get("/api/favorites/").data["count"], 1)
        self.client.post(f"/api/listings/{listing_id}/comments/", {"text": "Торг уместен?"})
        detail = self.client.get(f"/api/listings/{listing_id}/").data
        self.assertTrue(detail["is_favorite"])
        self.client.get(f"/api/listings/{listing_id}/")  # same visitor, same day: not counted twice

        res = self.client.post("/api/chats/", {"listing": listing_id, "text": "Здравствуйте!"})
        self.assertEqual(res.status_code, 201)
        chat_id = res.data["id"]
        self.assertEqual(self.client.get(f"/api/listings/{listing_id}/stats/").status_code, 403)

        self.auth(self.seller)
        self.assertEqual(self.client.get("/api/chats/unread/").data["unread"], 1)
        msgs = self.client.get(f"/api/chats/{chat_id}/messages/").data
        self.assertEqual(msgs["count"], 1)
        self.client.post(f"/api/chats/{chat_id}/messages/", {"text": "Да, конечно"})
        self.assertEqual(self.client.get("/api/chats/unread/").data["unread"], 0)

        stats = self.client.get(f"/api/listings/{listing_id}/stats/").data
        self.assertEqual(stats["total_views"], 1)
        self.assertEqual(stats["favorites"], 1)
        self.assertEqual(stats["comments"], 1)
        self.assertEqual(stats["chats"], 1)
        self.assertEqual(Conversation.objects.get().seller, self.seller)

    def test_cannot_chat_with_self(self):
        self.auth(self.seller)
        listing_id = self.create_listing().data["id"]
        self.assertEqual(self.client.post("/api/chats/", {"listing": listing_id}).status_code, 400)

    def test_inactive_listing_hidden_from_public(self):
        self.auth(self.seller)
        listing_id = self.create_listing(is_active=False).data["id"]
        self.assertEqual(self.client.get("/api/listings/my/").data["count"], 1)
        self.client.credentials()
        self.assertEqual(self.client.get(f"/api/listings/{listing_id}/").status_code, 404)
        self.assertFalse(Listing.objects.get().is_active)
