#!/bin/bash
set -e

echo "Waiting for Neo4j to be ready..."
until cypher-shell -a bolt://neo4j:7687 -u neo4j -p dataops123 "RETURN 1" > /dev/null 2>&1; do
    sleep 3
done
echo "Neo4j is ready."

cypher-shell -a bolt://neo4j:7687 -u neo4j -p dataops123 -f /scripts/init-neo4j.cypher
echo "Neo4j seeded successfully."
