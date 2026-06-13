import unittest

from fastapi.testclient import TestClient

from main import app


class NagomiApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_reports_loaded_graph(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertGreater(body["graph"]["nodes"], 10_000)
        self.assertGreater(body["graph"]["edges"], 20_000)
        self.assertTrue(body["scheduled_transit"])
        self.assertIn(body["traffic_source"], {"tomtom_live", "delhi_time_model"})

    def test_route_plan_returns_all_profiles(self):
        response = self.client.post(
            "/routes",
            json={
                "source": {"lat": 28.6315, "lon": 77.2167},
                "destination": {"lat": 28.6129, "lon": 77.2295},
                "preference": "eco",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["recommended_route_id"], "eco")
        self.assertEqual(
            {route["id"] for route in body["routes"]},
            {"fastest", "cheapest", "eco", "safest"},
        )
        for route in body["routes"]:
            self.assertGreater(route["duration_minutes"], 0)
            self.assertGreater(route["distance_meters"], 0)
            self.assertGreaterEqual(len(route["geometry"]), 2)
            self.assertIn("traffic", route)
            self.assertIn("safety", route)
            self.assertGreater(route["safety"]["score"], 0)

    def test_long_trip_returns_multimodal_transit_option(self):
        response = self.client.post(
            "/routes",
            json={
                "source": {"lat": 28.5562, "lon": 77.1000},
                "destination": {"lat": 28.6562, "lon": 77.2410},
                "preference": "eco",
            },
        )

        self.assertEqual(response.status_code, 200)
        routes = response.json()["routes"]
        multimodal = [route for route in routes if len(route["legs"]) > 1]
        self.assertTrue(multimodal)
        transit_modes = {
            leg["mode"]
            for route in multimodal
            for leg in route["legs"]
        }
        self.assertTrue({"metro", "bus"} & transit_modes)

    def test_traffic_analysis_reports_source_and_delay(self):
        response = self.client.post(
            "/traffic",
            json={
                "source": {"lat": 28.6315, "lon": 77.2167},
                "destination": {"lat": 28.6288, "lon": 77.2410},
                "preference": "fastest",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["source"], {"tomtom_live", "delhi_time_model"})
        self.assertGreaterEqual(body["delay_multiplier"], 1)

    def test_place_search(self):
        response = self.client.get("/places", params={"q": "metro"})

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["places"]), 2)

    def test_local_frontend_origin_is_allowed(self):
        response = self.client.options(
            "/routes",
            headers={
                "Origin": "http://127.0.0.1:5174",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5174",
        )


if __name__ == "__main__":
    unittest.main()
