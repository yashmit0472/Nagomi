import osmnx as ox

place = "New Delhi, Delhi, India"

G = ox.graph_from_place(
    place,
    network_type="drive"
)

print(G)

ox.save_graphml(G, "delhi_graph.graphml")

print("Graph Saved!")