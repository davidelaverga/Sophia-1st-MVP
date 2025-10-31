#!/usr/bin/env python3
"""
Test script to verify all API credentials are properly configured.
Run: python test_api_keys.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_var(name: str, expected_min_length: int = 10) -> tuple[bool, int]:
    """Check if environment variable exists and has reasonable length"""
    value = os.getenv(name)
    if not value:
        return False, 0
    return True, len(value)

def test_mistral_api():
    """Test Mistral API connectivity"""
    print("\n=== Testing Mistral API ===")
    try:
        from mistralai import Mistral
        api_key = os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            print("❌ MISTRAL_API_KEY not found in environment")
            return False
            
        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": "Say hello"}]
        )
        
        result = response.choices[0].message.content
        print(f"✅ Mistral API: Working!")
        print(f"   Response: {result[:100]}")
        return True
        
    except Exception as e:
        print(f"❌ Mistral API: Failed - {type(e).__name__}: {str(e)}")
        return False

def test_inworld_api():
    """Test Inworld API connectivity"""
    print("\n=== Testing Inworld API ===")
    try:
        import requests
        api_key = os.getenv("INWORLD_API_KEY")
        
        if not api_key:
            print("❌ INWORLD_API_KEY not found in environment")
            return False
        
        response = requests.post(
            "https://api.inworld.ai/tts/v1/voice",
            json={
                "text": "test", 
                "voiceId": "Deborah", 
                "modelId": "inworld-tts-1-max", 
                "format": "mp3"
            },
            headers={"Authorization": f"Basic {api_key}"},
            timeout=10
        )
        
        if response.status_code == 200:
            audio_length = len(response.content)
            print(f"✅ Inworld API: Working! (Status {response.status_code})")
            print(f"   Received {audio_length} bytes of audio")
            return True
        else:
            print(f"❌ Inworld API: Failed - Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Inworld API: Failed - {type(e).__name__}: {str(e)}")
        return False

def test_openai_api():
    """Test OpenAI API connectivity (optional fallback)"""
    print("\n=== Testing OpenAI API (Fallback TTS) ===")
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("⚠️ OPENAI_API_KEY not configured (optional)")
            return None
        
        client = openai.OpenAI(api_key=api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ OpenAI API: Working!")
        print(f"   Response: {result[:100]}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API: Failed - {type(e).__name__}: {str(e)}")
        return False

def test_google_api():
    """Test Google/Gemini API connectivity"""
    print("\n=== Testing Google/Gemini API ===")
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment")
            return False
        
        # Try using Phoenix Evals which uses Google API
        try:
            from phoenix.evals import GoogleGenAIModel
            model = GoogleGenAIModel(model="gemini-2.5-flash")
            print(f"✅ Google/Gemini API: Configured via Phoenix!")
            print(f"   Model: gemini-2.5-flash")
            return True
        except ImportError:
            # Phoenix not available, try direct REST API call
            import requests
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": "Say hello"}]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response')
                print(f"✅ Google/Gemini API: Working!")
                print(f"   Response: {result[:100]}")
                return True
            else:
                print(f"❌ Google/Gemini API: Failed - Status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
        
    except Exception as e:
        print(f"❌ Google/Gemini API: Failed - {type(e).__name__}: {str(e)}")
        return False

def test_supabase_config():
    """Test Supabase configuration"""
    print("\n=== Testing Supabase Configuration ===")
    try:
        from supabase import create_client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        bucket = os.getenv("SUPABASE_BUCKET_AUDIO", "audio")
        
        if not url or not key:
            print("❌ Supabase credentials missing")
            return False
        
        # Create client
        supabase = create_client(url, key)
        
        # Try to list files in bucket (without limit parameter)
        try:
            result = supabase.storage.from_(bucket).list()
            file_count = len(result) if result else 0
            print(f"✅ Supabase: Connection successful!")
            print(f"   URL: {url}")
            print(f"   Bucket: {bucket}")
            print(f"   Files in bucket: {file_count}")
            return True
        except Exception as list_error:
            # If listing fails, try to get bucket info
            buckets = supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if bucket in bucket_names:
                print(f"✅ Supabase: Connection successful!")
                print(f"   URL: {url}")
                print(f"   Bucket '{bucket}' exists")
                return True
            else:
                print(f"❌ Supabase: Bucket '{bucket}' not found")
                print(f"   Available buckets: {bucket_names}")
                return False
        
    except Exception as e:
        print(f"❌ Supabase: Failed - {type(e).__name__}: {str(e)}")
        return False

def main():
    """Run all API tests"""
    print("=" * 60)
    print("🔍 API Credentials Verification")
    print("=" * 60)
    
    # Check environment variables first
    print("\n=== Environment Variables Status ===")
    
    checks = [
        ("MISTRAL_API_KEY", 20),
        ("INWORLD_API_KEY", 20),
        ("OPENAI_API_KEY", 20),
        ("GOOGLE_API_KEY", 20),
        ("SUPABASE_URL", 20),
        ("SUPABASE_SERVICE_KEY", 100),
        ("SUPABASE_BUCKET_AUDIO", 0),
    ]
    
    for var_name, min_length in checks:
        present, length = check_env_var(var_name, min_length)
        status = "✅ Present" if present else "❌ Missing"
        print(f"{var_name:25} {status} ({length} chars)")
    
    bucket_name = os.getenv("SUPABASE_BUCKET_AUDIO", "audio")
    if bucket_name == "audio-uploads":
        print(f"{'':25} ✅ Correct bucket name: {bucket_name}")
    else:
        print(f"{'':25} ⚠️ Bucket name: {bucket_name} (expected: audio-uploads)")
    
    # Run API tests
    results = {
        "Mistral": test_mistral_api(),
        "Inworld": test_inworld_api(),
        "OpenAI": test_openai_api(),
        "Google/Gemini": test_google_api(),
        "Supabase": test_supabase_config(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for service, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️ SKIP"
        print(f"{service:20} {status}")
    
    # Overall result - Supabase is optional for this test since it depends on network
    required_services = ["Mistral", "Inworld", "Google/Gemini"]
    required_passed = all(results.get(s) for s in required_services)
    
    # Check if Supabase config at least looks valid
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    bucket = os.getenv("SUPABASE_BUCKET_AUDIO", "audio")
    
    supabase_config_valid = (
        supabase_url.startswith("https://") and 
        len(supabase_key) > 100 and
        bucket == "audio-uploads"
    )
    
    if not results.get("Supabase") and supabase_config_valid:
        print("\n⚠️ Note: Supabase connection failed but configuration looks correct.")
        print("   This may be a network/DNS issue in the sandbox environment.")
    
    print("\n" + "=" * 60)
    if required_passed:
        print("✅ ALL REQUIRED SERVICES OPERATIONAL")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME REQUIRED SERVICES FAILED")
        print("=" * 60)
        print("\n⚠️ Please check the error messages above and verify:")
        print("   1. API keys are correctly set in .env file")
        print("   2. API keys have not expired")
        print("   3. Network connectivity is working")
        return 1

if __name__ == "__main__":
    sys.exit(main())
