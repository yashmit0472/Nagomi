import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from main import app
from services import places
from services.geo_routing import _build_legs


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

    def test_transit_legs_use_station_names_instead_of_transfer_labels(self):
        steps = [
            {
                "from_index": 0,
                "to_index": 1,
                "distance": 300,
                "time": 240,
                "instruction": {"text": "Walk northeast."},
            },
            {
                "from_index": 1,
                "to_index": 2,
                "distance": 20,
                "time": 20,
                "instruction": {
                    "text": "Enter the Brigadier Hoshiar Singh Station."
                },
            },
            {
                "from_index": 2,
                "to_index": 3,
                "distance": 9000,
                "time": 900,
                "instruction": {
                    "text": "Take the Green Line toward Inderlok. (8 stops)"
                },
            },
            {
                "from_index": 3,
                "to_index": 4,
                "distance": 25,
                "time": 25,
                "instruction": {"text": "Exit the Inderlok Station."},
            },
            {
                "from_index": 4,
                "to_index": 5,
                "distance": 180,
                "time": 140,
                "instruction": {"text": "Walk to the Red Line platform."},
            },
            {
                "from_index": 5,
                "to_index": 6,
                "distance": 15,
                "time": 15,
                "instruction": {"text": "Enter the Inderlok Station."},
            },
            {
                "from_index": 6,
                "to_index": 7,
                "distance": 7000,
                "time": 780,
                "instruction": {
                    "text": "Take the Red Line toward Shaheed Sthal. (7 stops)"
                },
            },
            {
                "from_index": 7,
                "to_index": 8,
                "distance": 20,
                "time": 20,
                "instruction": {"text": "Exit the Kashmere Gate Station."},
            },
            {
                "from_index": 8,
                "to_index": 9,
                "distance": 500,
                "time": 400,
                "instruction": {"text": "Walk southeast."},
            },
        ]
        points = [
            {"lat": 28.60 + index * 0.001, "lon": 77.10 + index * 0.001}
            for index in range(10)
        ]

        legs = _build_legs(steps, points)

        self.assertEqual(
            [(leg["label"], leg["from"], leg["to"]) for leg in legs],
            [
                (
                    "Walk",
                    "Starting point",
                    "Brigadier Hoshiar Singh Station - Green Line platform",
                ),
                (
                    "Green Line",
                    "Brigadier Hoshiar Singh Station - Green Line platform",
                    "Inderlok Station",
                ),
                (
                    "Walk",
                    "Inderlok Station",
                    "Inderlok Station - Red Line platform",
                ),
                (
                    "Red Line",
                    "Inderlok Station - Red Line platform",
                    "Kashmere Gate Station",
                ),
                ("Walk", "Kashmere Gate Station", "Destination"),
            ],
        )
        self.assertFalse(
            any(
                leg["from"] == "Transfer" or leg["to"] == "Transfer"
                for leg in legs
            )
        )

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
