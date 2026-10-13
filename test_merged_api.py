import json
import unittest
from app import create_app

class TestMergedAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flask_app = create_app({"TESTING": True})
        cls.client = cls.flask_app.test_client()

    def test_location_analysis_endpoint(self):
        res = self.client.post("/api/location-analysis", json={
            "latitude": 15.4589,
            "longitude": 75.0078,
            "acres": 2.5
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("administrative", data)
        self.assertIn("soil", data)
        self.assertIn("weather_summary", data)
        self.assertEqual(data["land_acres"], 2.5)

    def test_crop_recommendations_endpoint(self):
        res = self.client.get("/api/crop-recommendations?latitude=15.4589&longitude=75.0078&acres=2.5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("top_recommendations", data)
        self.assertGreaterEqual(len(data["top_recommendations"]), 3)
        crop_names = [c["crop"] for c in data["top_recommendations"]]
        self.assertIn("Maize", crop_names)

    def test_crop_budget_endpoint(self):
        res = self.client.get("/api/crop-budget?crop=Wheat&acres=3.0")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["crop"], "Wheat")
        self.assertEqual(data["acres"], 3.0)
        self.assertIn("total_cultivation_cost", data)
        self.assertGreater(data["total_cultivation_cost"], 0)

    def test_government_schemes_endpoint(self):
        res = self.client.get("/api/government-schemes?state=Karnataka&acres=2.5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total_found"], 1)
        self.assertIn("schemes", data)

    def test_farming_calendar_endpoint(self):
        res = self.client.get("/api/farming-calendar?crop=Wheat")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["name"], "Wheat")
        self.assertEqual(len(data["stages"]), 11)

    def test_missing_coordinates_returns_400(self):
        """Verifies no hardcoded coordinates fallback occurs."""
        res1 = self.client.post("/api/location-analysis", json={})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("required", res1.get_json().get("error", "").lower())

        res2 = self.client.get("/api/crop-recommendations")
        self.assertEqual(res2.status_code, 400)
        self.assertIn("required", res2.get_json().get("error", "").lower())

    def test_farm_profile_persistence_endpoints(self):
        """Verifies GET and POST /api/farm-profile SQLite persistence."""
        save_payload = {
            "full_name": "Farmer Basavaraj",
            "phone_number": "9123456789",
            "state": "Karnataka",
            "district": "Belagavi",
            "latitude": 15.8497,
            "longitude": 74.4977,
            "acres": 4.5,
            "irrigation": "Borewell / Irrigated",
            "soil_type": "Clay Loam"
        }
        res_post = self.client.post("/api/farm-profile", json=save_payload)
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.get_json()
        self.assertEqual(post_data["status"], "success")
        self.assertEqual(post_data["profile"]["full_name"], "Farmer Basavaraj")
        self.assertEqual(post_data["profile"]["district"], "Belagavi")
        self.assertEqual(post_data["profile"]["acres"], 4.5)

        # Retrieve the profile
        res_get = self.client.get("/api/farm-profile")
        self.assertEqual(res_get.status_code, 200)
        get_data = res_get.get_json()
        self.assertEqual(get_data["status"], "success")
        self.assertIsNotNone(get_data["profile"])
        self.assertEqual(get_data["profile"]["district"], "Belagavi")
        self.assertEqual(get_data["profile"]["latitude"], 15.8497)

    def test_web_routes_render_html(self):
        """Verifies GET /, /login, and /dashboard render expected templates."""
        # 1. Homepage
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)
        home_html = res_home.get_data(as_text=True)
        self.assertIn("KrishiMitra", home_html)
        self.assertIn("Get Started", home_html)
        self.assertIn("/login", home_html)

        # 2. Login Page
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        login_html = res_login.get_data(as_text=True)
        self.assertIn("Continue with Google", login_html)
        self.assertIn("btnGoogleAuth", login_html)
        self.assertIn("phone-panel", login_html)
        self.assertIn("recaptcha-container", login_html)

        # 3. Dashboard
        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        dash_html = res_dash.get_data(as_text=True)
        self.assertIn("Farm Geolocation & Parameters", dash_html)
        self.assertIn("userProfileBadge", dash_html)

    def test_sync_live_location_endpoint(self):
        """Verifies POST /api/sync-live-location fetches real Earth Engine & Open-Meteo data and updates memory."""
        res = self.client.post("/api/sync-live-location", json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "acres": 2.5,
            "session_id": "test_unit_live_sync_sess"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("detected_location", data)
        self.assertIn("soil_type", data)
        self.assertIn("temperature", data)
        self.assertIn("memory", data)
        self.assertEqual(data["memory"]["acres"], 2.5)
        self.assertTrue(len(data["memory"]["district"]) > 0)
        self.assertTrue(len(data["soil_type"]) > 0)



