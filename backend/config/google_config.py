# Google API Configuration
# Set your Google API key here or as environment variable

# Option 1: Set as environment variable (recommended)
# export GOOGLE_API_KEY="your_api_key_here"

# Option 2: Set directly in this file (less secure)
# GOOGLE_API_KEY = "your_api_key_here"

# Instructions:
# 1. Get your API key from: https://makersuite.google.com/app/apikey
# 2. Either:
#    - Set environment variable: export GOOGLE_API_KEY="your_key"
#    - Or uncomment and set GOOGLE_API_KEY above
#
# Then restart the Flask server

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_google_api_key():
    """Get Google API key from environment or config."""
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key == 'your_google_api_key_here':
        return None  # Treat placeholder as no key
    return api_key

def is_llm_enabled():
    """Check if LLM functionality is available."""
    return get_google_api_key() is not None
