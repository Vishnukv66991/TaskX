from supabase import create_client
import os
import sys
import ssl

# Disable SSL verification for Windows compatibility with Supabase
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

# Create SSL context that doesn't verify certificates
ssl._create_default_https_context = ssl._create_unverified_context

# Ensure config can be imported from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

def init_supabase():
    url = Config.SUPABASE_URL
    key = Config.SUPABASE_KEY
    if not url or not key:
        raise Exception("Supabase URL and Key must be defined in environment variables.")
    return create_client(url, key)

supabase = init_supabase()
