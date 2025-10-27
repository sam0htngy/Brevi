import os 
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try: 
    supabase.storage.create_bucket("videos", {"public": False})
    print("Video bucket created sucessfully")
except Exception as e:
    print (f"Bucket creation: {str(e)}")