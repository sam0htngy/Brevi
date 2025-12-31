import os
import jwt
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

current_folder = Path(__file__).resolve().parent
env_path = current_folder.parent / ".env"

load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("REACT_APP_SUPABASE_URL")
SUPABASE_KEY = os.getenv("REACT_APP_SUPABASE_KEY")

print (f"CURRENT URL: {SUPABASE_URL}")

print (f"--- DEBGUGGING TOOL ----")

try: 
    decoded = jwt.decode(SUPABASE_KEY, options= {"verify_signature": False})
    role = decoded.get("role")
    
    print (f"Key role: [{role}]")
    
    if role == "anon":
        print(" ERROR: using ANON key")
    elif role == "service_role":
        print(" Success you are using the service Key")
    else:
        print(f"Role should be {role}. should be instead service role")
except Exception as e:
    print(f"KEY ERROR: could not decode key not a vaild JWT {e}")
    exit()
    
print("\n--- DATABASE TEST ---")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # We try to insert a row with a random fake user_id
    # If this fails, it's because your table is enforcing a Foreign Key to auth.users
    print("Attempting insert...")
    data = {
        "title": "Debug Key Test",
        "video_url": "http://test.com",
        "user_id": "user_DEBUG_TESTING_123" 
    }
    response = supabase.table("projects").insert(data).execute()
    print("INSERT SUCCESS! Row created.")
    print("   If this worked, your API is fine, and the issue was likely caching.")

except Exception as e:
    print("INSERT FAILED!")
    error_msg = str(e)
    print(f"Error Details: {error_msg}")
    
    if "violates foreign key constraint" in error_msg:
        print("\nTHE PROBLEM IS FOUND: FOREIGN KEY CONSTRAINT")
        print("   Your 'user_id' column is linked to Supabase Auth.")
        print("   BUT you are using Clerk.")
        print("   FIX: Go to Supabase > Table Editor > user_id column > Edit > Remove Foreign Key.")
    
    if "403" in error_msg:
        print("\n STILL 403 FORBIDDEN")
        print("   If Key Role is 'service_role', checks your RLS Policies.")
        print("   Even Admins can be blocked if a Trigger or Policy explicitly denies 'service_role'.")

print("--- DIAGNOSTIC END ---")