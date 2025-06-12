import chromadb
import json
from sentence_transformers import SentenceTransformer
import os

# Configuration
CHROMA_DATA_PATH = "/Users/samanth/Project_AI/project_sam/backend/data/chroma_db_store"
COLLECTION_NAME = "admin_links_collection"
# Using a more powerful model for better semantic understanding
# This model provides higher quality embeddings for better search accuracy
MODEL_NAME = 'all-mpnet-base-v2' 

# Ensure the model is downloaded (SentenceTransformer handles this automatically on first use)
# You might want to ensure this happens during a setup phase if internet access is an issue at runtime.
try:
    embedding_model = SentenceTransformer(MODEL_NAME)
except Exception as e:
    print(f"Error loading SentenceTransformer model: {e}")
    embedding_model = None

def get_chroma_client():
    """Initializes and returns a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_DATA_PATH)

def get_or_create_collection(client):
    """Gets an existing collection or creates a new one if it doesn't exist."""
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        return collection
    except: # Broad exception to catch errors if collection doesn't exist
        print(f"Collection '{COLLECTION_NAME}' not found. Creating a new one.")
        # Create collection with cosine distance for similarity scoring
        # Cosine distance gives values between 0 (identical) and 2 (opposite)
        # We can convert to similarity: similarity = 1 - (distance / 2)
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}  # Use cosine distance
        )
        return collection

def is_collection_populated(collection):
    """Checks if the collection has any documents."""
    return collection.count() > 0

def populate_collection_from_json(collection, json_file_path="/Users/samanth/Project_AI/project_sam/backend/data/admin_links.json"):
    """
    Loads data from a JSON file, generates embeddings, and populates the ChromaDB collection.
    This function assumes the JSON file contains a list of objects,
    and each object has 'id', 'name', 'description', and 'keywords' fields.
    """
    if not embedding_model:
        print("Embedding model not available. Cannot populate collection.")
        return

    print(f"Populating collection '{COLLECTION_NAME}' from '{json_file_path}'...")
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}")
        return

    documents_to_add = []
    embeddings_to_add = []
    metadatas_to_add = []
    ids_to_add = []

    for item in data:
        # Use only keywords for embedding to focus on key terms
        text_to_embed = ' '.join(item.get('keywords', [])).strip()
        
        if not text_to_embed: # Skip if no keywords
            print(f"LOG_CHROMA_SERVICE: Skipping item with id '{str(item.get('id', 'Unknown ID'))}' due to empty keywords.")
            continue

        print(f"LOG_CHROMA_SERVICE: Sending text for ITEM embedding (ID: {str(item.get('id', 'Unknown ID'))}): '{text_to_embed[:150]}...'") # Log added
        try:
            embedding = embedding_model.encode(text_to_embed).tolist()
            print(f"LOG_CHROMA_SERVICE: Received embedding for item ID: {str(item.get('id', 'Unknown ID'))} (Shape: if numpy array: {len(embedding)} else: list of len {len(embedding)})") # Log added
        except Exception as e:
            print(f"Error encoding text for item id '{str(item.get('id', 'Unknown ID'))}': {e}")
            continue

        documents_to_add.append(text_to_embed) # Store the combined text as the document
        embeddings_to_add.append(embedding)
        
        # Ensure all metadata values are strings or other supported primitive types.
        # Replace None with an empty string or a placeholder string.
        # Store common_tasks as JSON string since ChromaDB doesn't support arrays
        common_tasks_json = json.dumps(item.get("common_tasks", [])) if item.get("common_tasks") else "[]"
        keywords_json = json.dumps(item.get("keywords", [])) if item.get("keywords") else "[]"
        
        metadata_entry = {
            "id": str(item.get("id", "N/A")),
            "name": str(item.get("name", "N/A")),
            "url_path": str(item.get("url_path", "N/A")),
            "description": str(item.get("description", "N/A")),
            "type": str(item.get("type", "N/A")),
            "keywords": keywords_json,  # Store keywords as JSON string
            "common_tasks": common_tasks_json
            # Add other fields you might want to filter by or retrieve, ensuring they are also sanitized
        }
        metadatas_to_add.append(metadata_entry)
        
        # ChromaDB IDs must be strings and unique. Ensure 'id' exists and is a string.
        item_id = item.get("id")
        if item_id is None:
            print(f"Warning: Item missing 'id'. Skipping item: {item.get('name', 'Unnamed item')}")
            # Remove the last added document and embedding if ID is missing, to keep lists consistent
            documents_to_add.pop()
            embeddings_to_add.pop()
            metadatas_to_add.pop() # Also remove the corresponding metadata entry
            continue
        ids_to_add.append(str(item_id))

    if documents_to_add:
        try:
            collection.add(
                embeddings=embeddings_to_add,
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            print(f"Successfully added {len(ids_to_add)} items to the collection.")
        except Exception as e:
            print(f"Error adding documents to Chroma collection: {e}")
    else:
        print("No documents were prepared to be added to the collection.")

def search_collection(collection, query_text, n_results=5):
    """
    Generates an embedding for the query text and searches the collection.
    """
    if not embedding_model:
        print("LOG_CHROMA_SERVICE: Embedding model not available. Cannot perform search.")
        return None
    
    if not query_text:
        print("LOG_CHROMA_SERVICE: Query text is empty. Cannot perform search.")
        return None

    print(f"LOG_CHROMA_SERVICE: Sending text for QUERY embedding: '{query_text}'") # Log added
    try:
        query_embedding = embedding_model.encode(query_text).tolist()
        print(f"LOG_CHROMA_SERVICE: Received embedding for query '{query_text}' (Shape: if numpy array: {len(query_embedding)} else: list of len {len(query_embedding)})") # Log added
    except Exception as e:
        print(f"LOG_CHROMA_SERVICE: Error encoding query text '{query_text}': {e}")
        return None
        
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=['metadatas', 'documents', 'distances'] # Specify what to include in results
        )
        return results
    except Exception as e:
        print(f"Error querying Chroma collection: {e}")
        return None

def ensure_collection_ready():
    """
    Ensures the ChromaDB collection is initialized and populated if necessary.
    Returns the collection object.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    
    if not is_collection_populated(collection):
        print(f"Collection '{COLLECTION_NAME}' is empty. Attempting to populate.")
        # Corrected path for admin_links.json
        populate_collection_from_json(collection, json_file_path="/Users/samanth/Project_AI/project_sam/backend/data/admin_links.json")
    else:
        print(f"Collection '{COLLECTION_NAME}' is already populated with {collection.count()} items.")
    return collection

def force_rebuild_collection(json_file_path="/Users/samanth/Project_AI/project_sam/backend/data/admin_links.json"):
    """
    Deletes the existing ChromaDB collection and rebuilds it from the specified JSON file.
    Returns a dictionary with status and message.
    """
    client = get_chroma_client()
    try:
        print(f"Attempting to delete existing collection: '{COLLECTION_NAME}'...")
        client.delete_collection(name=COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' deleted successfully.")
    except Exception as e:
        # This can happen if the collection doesn't exist, which is fine for a rebuild.
        print(f"Info: Could not delete collection '{COLLECTION_NAME}' (it might not exist yet): {e}")

    print(f"Creating and populating new collection '{COLLECTION_NAME}'...")
    # get_or_create_collection will now create it as it was just deleted or never existed
    new_collection = get_or_create_collection(client) 
    if new_collection:
        populate_collection_from_json(new_collection, json_file_path=json_file_path)
        count = new_collection.count()
        # Also update the global CHROMA_COLLECTION in routes.py if it's being used
        # This requires a bit more thought on how to signal routes.py to update its instance.
        # For now, the next call to get_chroma_collection_instance() in routes.py will fetch the new one.
        print(f"Collection '{COLLECTION_NAME}' rebuilt and populated with {count} items.")
        return {"status": "success", "message": f"Collection '{COLLECTION_NAME}' rebuilt successfully with {count} items."}
    else:
        error_msg = f"Failed to create new collection '{COLLECTION_NAME}' during rebuild."
        print(error_msg)
        return {"status": "error", "message": error_msg}


# Example of how to use (can be removed or placed in a main execution block)
if __name__ == '__main__':
    print("Chroma Service - Main Execution Block (for testing)")
    
    # 1. Ensure collection is ready (creates and populates if needed)
    collection = ensure_collection_ready()

    if collection and embedding_model:
        # 2. Test search
        print("\nTesting search functionality...")
        test_queries = ["user management", "how to add product", "dashboard overview"]
        for query in test_queries:
            print(f"\nSearching for: '{query}'")
            search_results = search_collection(collection, query, n_results=2)
            if search_results:
                print("Search Results:")
                # ChromaDB returns lists of lists for ids, documents, metadatas, distances
                # because you can query with multiple embeddings at once.
                # Here we queried with one embedding, so we take the first element.
                ids = search_results.get('ids', [[]])[0]
                docs = search_results.get('documents', [[]])[0]
                metas = search_results.get('metadatas', [[]])[0]
                dists = search_results.get('distances', [[]])[0]

                for i in range(len(ids)):
                    print(f"  ID: {ids[i]}, Distance: {dists[i]:.4f}")
                    print(f"  Metadata: {metas[i]}")
                    # print(f"  Document: {docs[i]}") # The combined text used for embedding
            else:
                print("No results found or error during search.")
    else:
        if not collection:
            print("Failed to initialize or get Chroma collection.")
        if not embedding_model:
            print("Embedding model failed to load. Search functionality will not work.")

