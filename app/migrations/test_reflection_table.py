# test_reflection_table.py
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

try:
    result = supabase.table("reflection_cards").select("*").limit(1).execute()
    print("✅ Tabla reflection_cards existe y funciona!")
except Exception as e:
    print(f"❌ Tabla no existe: {e}")
    print("⚠️  Ejecuta la migración SQL en Supabase Dashboard")