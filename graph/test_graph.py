import osmnx as ox

G = ox.load_graphml("delhi_graph.graphml")

print("Nodes:", len(G.nodes))
print("Edges:", len(G.edges))

node = list(G.nodes())[0]

print("\nSample Node:")
print(node)

print("\nNode Attributes:")
print(G.nodes[node])
