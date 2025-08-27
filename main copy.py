from supabase import create_client
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv(r"C:\Users\ajdee\Sophia-1st-MVP (2)\Sophia-1st-MVP\.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL command to drop old foreign key and create a new one
alter_fk_sql = """
-- Drop the existing foreign key constraint
ALTER TABLE public.conversation_sessions
DROP CONSTRAINT IF EXISTS conversation_sessions_user_id_fkey;

-- Create a new foreign key pointing to public.users.id
ALTER TABLE public.conversation_sessions
ADD CONSTRAINT conversation_sessions_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES public.users(id)
ON UPDATE CASCADE
ON DELETE CASCADE;
"""

# Execute the SQL
response = supabase.rpc("execute_sql", {"sql": alter_fk_sql}).execute()
print(response)
