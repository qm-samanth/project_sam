import google.generativeai as genai
import json
import os
from typing import List, Dict, Any
from config.google_config import get_google_api_key, is_llm_enabled

def configure_gemini():
    """Configure the Gemini API with your API key."""
    if not is_llm_enabled():
        print("WARNING: Google API key not configured! LLM re-ranking disabled.")
        return None
    
    genai.configure(api_key=get_google_api_key())
    model = genai.GenerativeModel('gemini-1.5-flash')  # Fast and efficient model
    return model

def create_lightweight_payload(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a lightweight payload for LLM by including only essential data.
    Includes keywords for better matching but removes heavy common_tasks array.
    """
    lightweight_results = []
    
    for result in search_results:
        # Extract essential fields including keywords for better LLM matching
        keywords = result.get("keywords", [])
        # Join ALL keywords as a searchable string - don't truncate for better matching
        keywords_text = ", ".join(keywords) if keywords else ""
        
        lightweight_result = {
            "id": result.get("id"),
            "name": result.get("name"),
            "description": result.get("description", "")[:300],  # Increased from 200 to 300
            "keywords": keywords_text,  # Include keywords for better matching
            "type": result.get("type"),
            "relevance_score": result.get("relevance_score", 0)
        }
        lightweight_results.append(lightweight_result)
    
    return lightweight_results

def rerank_search_results(user_query: str, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use Gemini LLM to re-rank search results based on functional relevance.
    Optimized for speed by sending only essential data to LLM.
    
    Args:
        user_query: The original user search query
        search_results: List of results from ChromaDB semantic search
        
    Returns:
        Re-ranked list of results with LLM relevance scores
    """
    model = configure_gemini()
    if not model:
        print("Gemini not configured, returning original results")
        return search_results
    
    # Create lightweight payload for faster processing
    lightweight_results = create_lightweight_payload(search_results)
    
    # Prepare the optimized prompt for LLM analysis
    prompt = f"""
You are an expert assistant helping users find admin functionality.

USER QUERY: "{user_query}"

SEARCH RESULTS:
{json.dumps(lightweight_results, indent=1)}

TASK:
1. Analyze which result name/description/keywords best matches the user's query
2. Look carefully at the keywords field for specific functionality matches
3. Be selective but not overly strict with relevance scores
4. Scoring guidelines:
   - 85-100: Perfect match - exact functionality found in name/description/keywords
   - 60-84: Good match - related functionality  
   - 0-59: Poor match - filter out

RESPONSE FORMAT (JSON only):
[
  {{
    "id": "result_id",
    "llm_relevance_score": 85,
    "llm_explanation": "Brief reason why this matches"
  }}
]
"""

    try:
        print(f"Sending lightweight search results to Gemini for re-ranking...")
        print(f"DEBUG: LLM Prompt Data: {json.dumps(lightweight_results, indent=2)}")
        response = model.generate_content(prompt)
        
        # Parse the LLM response
        llm_response = response.text.strip()
        
        # Remove markdown code blocks if present
        if llm_response.startswith('```json'):
            llm_response = llm_response[7:]
        if llm_response.startswith('```'):
            llm_response = llm_response[3:]
        if llm_response.endswith('```'):
            llm_response = llm_response[:-3]
        
        reranked_results = json.loads(llm_response)
        print(f"DEBUG: LLM returned {len(reranked_results)} re-ranked results")
        print(f"DEBUG: Raw LLM Response: {response.text}")
        print(f"DEBUG: Parsed LLM Results: {json.dumps(reranked_results, indent=2)}")
        
        # Map the LLM results back to original data
        final_results = []
        original_results_map = {r.get("id"): r for r in search_results}
        
        for llm_result in reranked_results:
            result_id = llm_result.get("id")
            if result_id in original_results_map:
                original_data = original_results_map[result_id].copy()
                original_data['llm_relevance_score'] = llm_result.get('llm_relevance_score', 0)
                original_data['llm_explanation'] = llm_result.get('llm_explanation', '')
                final_results.append(original_data)
        
        print(f"LLM successfully re-ranked {len(final_results)} results")
        return final_results
        
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        print(f"LLM Response: {response.text}")
        return search_results
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return search_results

def generate_natural_response(user_query: str, search_results: List[Dict[str, Any]]) -> str:
    """
    Generate a natural language response with clickable links for the user.
    
    Args:
        user_query: The original user search query
        search_results: Filtered high-relevance results
        
    Returns:
        Natural language response with clickable links
    """
    model = configure_gemini()
    if not model or not search_results:
        return f"I couldn't find any relevant results for '{user_query}'. Please try different keywords."
    
    # Prepare results summary for LLM
    results_summary = []
    for result in search_results:
        results_summary.append({
            "name": result.get("name"),
            "description": result.get("description", "")[:150],
            "url": result.get("url_path"),
            "relevance_score": result.get("llm_relevance_score", 0)
        })
    
    prompt = f"""
You are a helpful assistant guiding users to the right admin functionality.

USER QUERY: "{user_query}"

RELEVANT RESULTS FOUND:
{json.dumps(results_summary, indent=1)}

TASK: Write a natural, conversational response that:
1. Confirms you found the exact functionality they need
2. Provides a clear, clickable link in markdown format: [Link Text](URL)  
3. Mentions the specific functionality when possible
4. Is confident and helpful (not vague or uncertain)

EXAMPLE FORMAT:
"Perfect! I found exactly what you need for Google Map zoom settings.

You can adjust the Google Map zoom level in the [Offersites Settings](https://teamvelocityportal.com/OfferSites/Setup/) section. This page includes a 'Set Google Map Zoom' option along with many other website display and functionality settings.

This will let you control how zoomed in or out the maps appear on your website."

Write a similar helpful response for the user's query:
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating natural response: {e}")
        # Fallback to simple response
        if search_results:
            result = search_results[0]
            return f"I found what you're looking for! Check out [{result.get('name')}]({result.get('url_path')}) for '{user_query}' functionality."
        return f"I couldn't find specific results for '{user_query}'. Please try different keywords."

def extract_reranked_results(llm_results: List[Dict[str, Any]], min_llm_score: int = 60) -> List[Dict[str, Any]]:
    """
    Filter results to only include those with high LLM relevance scores.
    
    Args:
        llm_results: Results from LLM with llm_relevance_score
        min_llm_score: Minimum LLM relevance score to include (default: 70)
        
    Returns:
        Filtered results with only high-relevance items
    """
    enhanced_results = []
    
    for result in llm_results:
        llm_score = result.get('llm_relevance_score', 0)
        
        # Only include results with high LLM relevance scores
        if llm_score >= min_llm_score:
            enhanced_results.append(result)
            print(f"Including result: '{result.get('name')}' with LLM score: {llm_score}")
        else:
            print(f"Filtering out result: '{result.get('name')}' with low LLM score: {llm_score}")
    
    print(f"LLM filtering: {len(llm_results)} original → {len(enhanced_results)} relevant results")
    return enhanced_results
