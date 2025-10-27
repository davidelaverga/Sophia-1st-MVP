#!/usr/bin/env python3
"""
Test script for Voxtral streaming API with WAV files from the project.
This script will help debug why Voxtral streaming is yielding 0 tokens.
"""

import os
import base64
import json
from pathlib import Path
from mistralai import Mistral

def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def test_voxtral_streaming(wav_file_path: str):
    """Test Voxtral streaming with a WAV file"""
    
    # Load API key
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print("❌ MISTRAL_API_KEY not found in environment")
        return False
    
    print(f"🔑 Using API key: {api_key[:10]}...")
    
    # Load WAV file
    if not os.path.exists(wav_file_path):
        print(f"❌ WAV file not found: {wav_file_path}")
        return False
    
    with open(wav_file_path, 'rb') as f:
        wav_bytes = f.read()
    
    print(f"📁 Loaded WAV file: {wav_file_path}")
    print(f"📊 File size: {len(wav_bytes)} bytes")
    
    # Encode to base64
    audio_b64 = base64.b64encode(wav_bytes).decode('utf-8')
    print(f"📝 Base64 encoded length: {len(audio_b64)} characters")
    
    # Initialize Mistral client
    try:
        client = Mistral(api_key=api_key)
        print("✅ Mistral client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Mistral client: {e}")
        return False
    
    # Test 1: Regular transcription (non-streaming)
    print("\n🧪 Test 1: Regular transcription")
    try:
        result = client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes, "audio/wav"),
            model="whisper-large-v3"
        )
        print(f"✅ Transcription: '{result.text}'")
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
    
    # Test 2: Voxtral chat streaming with audio
    print("\n🧪 Test 2: Voxtral chat streaming")
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please transcribe and respond to this audio message about DeFi."
                    },
                    {
                        "type": "input_audio",
                        "input_audio": audio_b64
                    }
                ]
            }
        ]
        
        print("📤 Sending streaming request...")
        stream = client.chat.stream(
            model="voxtral-mini-latest",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        tokens_received = 0
        full_response = ""
        
        print("📥 Receiving stream...")
        for chunk in stream:
            print(f"🔍 Chunk type: {type(chunk)}")
            print(f"🔍 Chunk content: {chunk}")
            
            # Handle CompletionEvent wrapper
            if hasattr(chunk, 'data'):
                chunk_data = chunk.data
            else:
                chunk_data = chunk
            
            if hasattr(chunk_data, 'choices') and chunk_data.choices:
                choice = chunk_data.choices[0]
                if hasattr(choice, 'delta') and choice.delta:
                    if hasattr(choice.delta, 'content') and choice.delta.content:
                        content = choice.delta.content
                        print(f"📝 Token: '{content}'")
                        full_response += content
                        tokens_received += 1
                    else:
                        print("⚠️ Delta has no content")
                else:
                    print("⚠️ Choice has no delta")
            else:
                print("⚠️ Chunk has no choices")
        
        print(f"\n✅ Streaming completed!")
        print(f"📊 Tokens received: {tokens_received}")
        print(f"📝 Full response: '{full_response}'")
        
        if tokens_received == 0:
            print("❌ No tokens received from Voxtral streaming!")
            return False
        else:
            print("✅ Voxtral streaming working correctly!")
            return True
            
    except Exception as e:
        print(f"❌ Voxtral streaming failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_all_samples():
    """Test all WAV samples in the audio directory"""
    audio_dir = Path(__file__).parent / 'audio'
    wav_files = list(audio_dir.glob('*.wav'))
    
    print(f"🎵 Found {len(wav_files)} WAV files")
    
    success_count = 0
    for wav_file in wav_files[:3]:  # Test first 3 files
        print(f"\n{'='*60}")
        print(f"Testing: {wav_file.name}")
        print(f"{'='*60}")
        
        if test_voxtral_streaming(str(wav_file)):
            success_count += 1
    
    print(f"\n🏁 Summary: {success_count}/{min(3, len(wav_files))} tests passed")

if __name__ == "__main__":
    print("🚀 Voxtral Streaming Test Script")
    print("=" * 50)
    
    # Load environment
    load_env()
    
    # Test with a specific file first
    test_file = Path(__file__).parent / 'audio' / 'neutral_sample.wav'
    if test_file.exists():
        print(f"\n🎯 Testing with: {test_file.name}")
        test_voxtral_streaming(str(test_file))
    
    # Test multiple samples
    print(f"\n🔄 Testing multiple samples...")
    test_all_samples()
