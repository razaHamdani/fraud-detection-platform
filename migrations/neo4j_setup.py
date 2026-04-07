"""Create Neo4j constraints and indexes for the fraud graph."""
import os

from neo4j import GraphDatabase


def setup_neo4j():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "fraud_pass")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            "CREATE CONSTRAINT card_token IF NOT EXISTS FOR (c:Card) REQUIRE c.token IS UNIQUE",
            "CREATE CONSTRAINT device_fp IF NOT EXISTS FOR (d:Device) REQUIRE d.fingerprint IS UNIQUE",
            "CREATE CONSTRAINT ip_addr IF NOT EXISTS FOR (i:IP) REQUIRE i.address IS UNIQUE",
            "CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (m:Merchant) REQUIRE m.merchant_id IS UNIQUE",
        ]
        for cypher in constraints:
            print(f"Running: {cypher[:60]}...")
            session.run(cypher)
            print("  Done.")
    driver.close()


if __name__ == "__main__":
    setup_neo4j()
