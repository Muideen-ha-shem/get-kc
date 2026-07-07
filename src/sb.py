import os
from dotenv import load_dotenv
from supabase import create_client, Client



def get_client()-> Client:

    """

    This function creates a Supabase client using the URL and key from environment variables.

    """

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing Supabase Credentials")
    return create_client(url, key)