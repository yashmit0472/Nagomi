import osmnx as ox
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

GRAPH_PATH = BASE_DIR / "data" / "graphs" / "delhi_graph.graphml"

G = ox.load_graphml(str(GRAPH_PATH))

source = ox.distance.nearest_nodes(
    G,
    77.20975458212877,
    28.61534392056683
)

destination = ox.distance.nearest_nodes(
    G,
    77.21696179495987,
    28.661921912256247
)

route = ox.shortest_path(
    G,
    source,
    destination,
    weight="length"
)

fig, ax = ox.plot_graph_route(
    G,
    route,
    route_linewidth=4,
    node_size=0
)