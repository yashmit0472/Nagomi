import osmnx as ox
import matplotlib.pyplot as plt

G = ox.load_graphml("../data/graphs/delhi_graph.graphml")

source = ox.distance.nearest_nodes(
    G,
    77.2167,
    28.6315
)

destination = ox.distance.nearest_nodes(
    G,
    77.2090,
    28.6139
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
    node_size=0,
    show=False,
    close=False
)

plt.show()