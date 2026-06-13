import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from main import app
from services import places


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
                "source": {"lat": 28.6315, "lon": 77.2167},
                "destination": {"lat": 28.5494, "lon": 77.2001},
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

    @patch("services.routing._geoapify_fallback")
    def test_outside_local_graph_uses_whole_delhi_fallback(self, fallback):
        fallback.return_value = {
            "success": True,
            "recommended_route_id": "fastest",
            "routes": [{"id": "fastest"}],
            "routing_mode": "geoapify_whole_delhi",
        }

        response = self.client.post(
            "/routes",
            json={
                "source": {"lat": 28.5528, "lon": 77.0574},
                "destination": {"lat": 28.7384, "lon": 77.1399},
                "preference": "fastest",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["routing_mode"], "geoapify_whole_delhi")
        fallback.assert_called_once()

    @patch("services.routing._geoapify_fallback", return_value=None)
    def test_disconnected_local_nodes_return_clean_error(self, _fallback):
        response = self.client.post(
            "/routes",
            json={
                "source": {"lat": 28.6315, "lon": 77.2167},
                "destination": {"lat": 28.5672, "lon": 77.2100},
                "preference": "fastest",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("No connected local road route", response.json()["message"])

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
        self.assertIn(response.json()["source"], {"geoapify", "local_graph"})

    def test_place_search_indexes_named_roads_from_graph(self):
        response = self.client.get("/places", params={"q": "Nelson Mandela"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(
            any("Nelson Mandela" in place["name"] for place in body["places"])
        )
        self.assertTrue(
            any(place["provider"] == "local_graph" for place in body["places"])
        )

    def test_geoapify_results_are_bounded_provider_results(self):
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "features": [
                {
                    "properties": {
                        "place_id": "dwarka-sector-21",
                        "name": "Dwarka Sector 21",
                        "address_line2": "Dwarka, New Delhi, Delhi",
                        "lat": 28.5524,
                        "lon": 77.0583,
                    }
                }
            ]
        }

        original_key = places.GEOAPIFY_API_KEY
        places.GEOAPIFY_API_KEY = "test-key"
        places._geoapify_search.cache_clear()
        try:
            with patch("services.places.httpx.get", return_value=fake_response) as request:
                response = self.client.get("/places", params={"q": "Dwarka 21"})
        finally:
            places.GEOAPIFY_API_KEY = original_key
            places._geoapify_search.cache_clear()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "geoapify")
        self.assertEqual(body["places"][0]["name"], "Dwarka Sector 21")
        self.assertEqual(body["places"][0]["provider"], "geoapify")
        self.assertEqual(request.call_args.kwargs["params"]["filter"], places.DELHI_RECT)

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
