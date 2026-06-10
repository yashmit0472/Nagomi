import os
import osmnx as ox
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv("../backend/.env")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USER"),
        os.getenv("NEO4J_PASSWORD")
    )
)

G = ox.load_graphml("delhi_graph.graphml")

print("Preparing nodes...")

nodes = []

for node_id, data in G.nodes(data=True):
    nodes.append({
        "id": str(node_id),
        "lat": float(data.get("y", 0)),
        "lon": float(data.get("x", 0)),
        "street_count": int(data.get("street_count", 0))
    })

print(f"Nodes prepared: {len(nodes)}")

with driver.session() as session:

    batch_size = 1000

    for i in range(0, len(nodes), batch_size):

        batch = nodes[i:i + batch_size]

        session.run(
            """
            UNWIND $nodes AS node

            MERGE (n:Intersection {id: node.id})

            SET n.lat = node.lat,
                n.lon = node.lon,
                n.street_count = node.street_count
            """,
            nodes=batch
        )

        print(
            f"Imported nodes: {min(i + batch_size, len(nodes))}/{len(nodes)}"
        )

print("Node import completed!")

driver.close()