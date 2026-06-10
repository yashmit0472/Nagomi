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

print("Preparing edges...")

edges = []

for u, v, k, data in G.edges(keys=True, data=True):
    edges.append({
        "source": str(u),
        "target": str(v),
        "length": float(data.get("length", 0))
    })

print(f"Edges prepared: {len(edges)}")

with driver.session() as session:

    batch_size = 1000

    for i in range(0, len(edges), batch_size):

        batch = edges[i:i+batch_size]

        session.run(
            """
            UNWIND $edges AS edge

            MATCH (a:Intersection {id: edge.source})
            MATCH (b:Intersection {id: edge.target})

            MERGE (a)-[:ROAD {
                length: edge.length
            }]->(b)
            """,
            edges=batch
        )

        print(
            f"Imported edges: {min(i+batch_size,len(edges))}/{len(edges)}"
        )

print("Edge import completed!")

driver.close()