from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

# Connect to local Qdrant
client = QdrantClient(url="http://localhost:6333")

# Create a simple collection
client.recreate_collection(
    collection_name="test_collection",
    vectors_config=VectorParams(size=4, distance=Distance.COSINE)
)

# Insert a vector
client.upsert(
    collection_name="test_collection",
    points=[
        {
            "id": 1,
            "vector": [0.1, 0.2, 0.3, 0.4],
            "payload": {"type": "Non-PI", "text": "Sample content"}
        }
    ]
)

# Search for similar vectors
hits = client.search(
    collection_name="test_collection",
    query_vector=[0.1, 0.2, 0.25, 0.35],
    limit=3
)

print(hits)
