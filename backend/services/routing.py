from pathlib import Path
import osmnx as ox

# -----------------------------
# Load Graph Once
# -----------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent

GRAPH_PATH = (
    BASE_DIR
    / "data"
    / "graphs"
    / "delhi_graph.graphml"
)

print("Loading graph...")
G = ox.load_graphml(str(GRAPH_PATH))
print("Graph loaded successfully!")


# -----------------------------
# Route Function
# -----------------------------

def get_route(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float
):

    # -----------------------------
    # Find nearest nodes
    # -----------------------------

    source_node = ox.distance.nearest_nodes(
        G,
        source_lon,
        source_lat
    )

    destination_node = ox.distance.nearest_nodes(
        G,
        dest_lon,
        dest_lat
    )

    # -----------------------------
    # Shortest Path
    # -----------------------------

    route = ox.shortest_path(
        G,
        source_node,
        destination_node,
        weight="length"
    )

    if route is None:
        return {
            "success": False,
            "message": "No route found"
        }

    # -----------------------------
    # Distance Calculation
    # -----------------------------

    distance = 0

    for u, v in zip(route[:-1], route[1:]):

        edge_data = G.get_edge_data(u, v)

        if not edge_data:
            continue

        edge = min(
            edge_data.values(),
            key=lambda e: e.get("length", float("inf"))
        )

        distance += edge.get("length", 0)

    # -----------------------------
    # Extract Full Route Geometry
    # -----------------------------

    route_coordinates = []

    for u, v in zip(route[:-1], route[1:]):

        edge_data = G.get_edge_data(u, v)

        if not edge_data:
            continue

        edge = min(
            edge_data.values(),
            key=lambda e: e.get("length", float("inf"))
        )

        # Edge has geometry
        if "geometry" in edge:

            coords = list(edge["geometry"].coords)

            for lon, lat in coords:

                route_coordinates.append({
                    "lat": lat,
                    "lon": lon
                })

        # Edge has no geometry
        else:

            route_coordinates.append({
                "lat": G.nodes[u]["y"],
                "lon": G.nodes[u]["x"]
            })

            route_coordinates.append({
                "lat": G.nodes[v]["y"],
                "lon": G.nodes[v]["x"]
            })

    print("Source Node:", source_node)
    print("Destination Node:", destination_node)
    print("Route Nodes:", len(route))
    print("Route Coordinates:", len(route_coordinates))

    return {
        "success": True,
        "source_node": source_node,
        "destination_node": destination_node,
        "distance_meters": round(distance, 2),
        "route_nodes": len(route),
        "route": route_coordinates
    }