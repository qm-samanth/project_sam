# API routes and endpoint definitions
# Example (Flask):
# from flask import Blueprint, request, jsonify
# from core.main_processor import process_query # Assuming you have a main processing function
#
# api_bp = Blueprint('api', __name__)
#
# @api_bp.route('/query', methods=['POST'])
# def handle_query():
#     data = request.get_json()
#     query_text = data.get('query')
#     if not query_text:
#         return jsonify({'error': 'Query not provided'}), 400
#
#     response = process_query(query_text)
#     return jsonify(response)

import os
import json
from flask import Blueprint, request, jsonify
# from backend.core.retrieval.chroma_service import ensure_collection_ready, search_collection, force_rebuild_collection # Old import
from core.chroma_service import ensure_collection_ready, search_collection, force_rebuild_collection # New import

# Create a Blueprint for API routes
api_bp = Blueprint('api', __name__)

# Removed global variables for in-memory embeddings as ChromaDB handles persistence
# Removed path definitions for ADMIN_LINKS_FILE as it's handled by chroma_service

# The get_llm_client and load_and_embed_admin_links functions are no longer needed here
# if chroma_service.py is handling all embedding and storage.

# Initialize ChromaDB collection when the application starts or on first request.
# Calling ensure_collection_ready() here or within create_app() in app.py is a good practice.
# For simplicity in this focused change, we'll ensure it's ready within the search route first.
# A global variable for the collection can be used if initialized at app startup.
CHROMA_COLLECTION = None

def get_chroma_collection_instance():
    """Ensures ChromaDB is ready and returns the collection instance."""
    global CHROMA_COLLECTION
    if CHROMA_COLLECTION is None:
        print("Chroma collection not initialized. Ensuring it is ready...")
        CHROMA_COLLECTION = ensure_collection_ready()
        if CHROMA_COLLECTION:
            print("Chroma collection is now ready.")
        else:
            print("Failed to initialize Chroma collection.")
    return CHROMA_COLLECTION

@api_bp.route('/search', methods=['POST'])
def search():
    """
    API endpoint to receive a text query, perform semantic search using ChromaDB,
    and return results.
    Expects a JSON payload with a "text" field.
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing "text" field in JSON payload'}), 400

    input_text = data['text']
    if not input_text.strip():
        return jsonify({'error': 'Query text cannot be empty'}), 400

    # Get similarity threshold from request (optional, defaults to 0.4 for debugging)
    # Set similarity threshold - cosine similarity ranges from 0 to 1
    # 0.7 means we want results that are at least 70% similar
    similarity_threshold = data.get('threshold', 0.7)

    # Get the ChromaDB collection instance (ensures it's initialized and populated)
    collection = get_chroma_collection_instance()

    if not collection:
        error_msg = "ChromaDB service is not available or failed to initialize. Cannot perform search."
        print(f"Search Error: {error_msg}")
        return jsonify({'error': error_msg}), 503 # Service Unavailable

    print(f"Performing search in ChromaDB for: '{input_text}' with threshold: {similarity_threshold}")
    search_results = search_collection(collection, input_text, n_results=10) # Get more results to filter

    if search_results is None:
        # This case is handled if search_collection itself had an internal error and returned None
        return jsonify({'message': f'Search failed for query "{input_text}". Check server logs.'}), 500

    # Process ChromaDB results
    # search_results structure from chroma_service:
    # {'ids': [[id1, id2]], 'documents': [[doc1, doc2]], 'metadatas': [[meta1, meta2]], 'distances': [[dist1, dist2]]}
    # Since we query with one embedding, we take the first list from each.
    
    ids = search_results.get('ids', [[]])[0]
    # documents = search_results.get('documents', [[]])[0] # Raw documents used for embedding
    metadatas = search_results.get('metadatas', [[]])[0]
    distances = search_results.get('distances', [[]])[0]

    if not ids:
        return jsonify({'results': [], 'message': f'No results found for "{input_text}".'}), 200

    formatted_results = []
    for i in range(len(ids)):
        # Convert cosine distance to similarity score
        # Cosine distance ranges from 0 (identical) to 2 (opposite)
        # Convert to similarity: similarity = 1 - (distance / 2)
        # This gives us values from 1 (identical) to 0 (opposite)
        cosine_distance = distances[i]
        relevance_score = 1 - (cosine_distance / 2)
        
        # Debug logging to see actual scores
        link_info = metadatas[i]
        if link_info:
            print(f"DEBUG: Result {i+1}: '{link_info.get('name')}' - Distance: {cosine_distance:.3f}, Similarity: {relevance_score:.3f} (threshold: {similarity_threshold})")
        
        # Only include results above the similarity threshold
        if relevance_score >= similarity_threshold:
            if link_info: # Ensure metadata is not None
                formatted_results.append({
                    "id": link_info.get('id'), # from metadata
                    "name": link_info.get('name'),
                    "url_path": link_info.get('url_path'),
                    "description": link_info.get('description'),
                    "type": link_info.get('type'),
                    "relevance_score": relevance_score
                })
            else:
                # This case should ideally not happen if data is populated correctly
                print(f"Warning: Missing metadata for result with ID {ids[i]}")

    # Debug: Show total results found vs filtered
    print(f"DEBUG: Found {len(ids)} total results, {len(formatted_results)} above threshold {similarity_threshold}")

    # If no results meet the threshold, return empty results with message
    if not formatted_results:
        return jsonify({
            'results': [], 
            'message': f'No relevant results found for "{input_text}". Please try different keywords.'
        }), 200

    # Sort by relevance score (descending) and limit to top 5
    formatted_results.sort(key=lambda x: x['relevance_score'], reverse=True)
    formatted_results = formatted_results[:5]

    return jsonify({
        'query': input_text,
        'results': formatted_results
    })

@api_bp.route('/rebuild-index', methods=['GET'])
def rebuild_chroma_index():
    """
    API endpoint to manually trigger a rebuild of the ChromaDB collection 
    from the source JSON file.
    """
    print("Received request to rebuild ChromaDB index...")
    # Optionally, add authentication/authorization here for sensitive operations
    
    # Call the force_rebuild_collection function from chroma_service
    rebuild_status = force_rebuild_collection()
    
    # Update the global CHROMA_COLLECTION instance in this module
    # so subsequent searches use the newly rebuilt collection immediately without needing a restart.
    global CHROMA_COLLECTION
    CHROMA_COLLECTION = None # Clear the current instance
    CHROMA_COLLECTION = get_chroma_collection_instance() # Re-initialize to get the new one
    
    if rebuild_status.get("status") == "success":
        print(f"Index rebuild successful: {rebuild_status.get('message')}")
        return jsonify(rebuild_status), 200
    else:
        print(f"Index rebuild failed: {rebuild_status.get('message')}")
        return jsonify(rebuild_status), 500

# Example of how to register this blueprint in your main app.py:
# from .routes import api_bp
# app.register_blueprint(api_bp, url_prefix='/api')
