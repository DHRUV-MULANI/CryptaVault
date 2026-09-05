"""Test connection to user's Supabase project."""

import os
import sys

from dotenv import load_dotenv

from supabase import Client, create_client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

print(f"Connecting to Supabase at: {supabase_url}")

if not supabase_url or not supabase_key:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY")
    sys.exit(1)

try:
    supabase: Client = create_client(supabase_url, supabase_key)
    print("Client initialized successfully.")

    # Check if we can query health or auth
    auth_resp = supabase.auth.get_user()
    print("Auth service reachable.")

    # Try querying feature_flags or profiles
    res = supabase.table("profiles").select("*").limit(1).execute()
    print(f"Database query response received: {res.data}")
except Exception as e:
    print(f"Supabase query status: {e}")
