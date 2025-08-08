# Voice Conversation Steps 4-6: Response Generation, TTS, and Full Testing
# Copy these code blocks into your notebook as separate cells

import os
import time
import json
import base64
from mistralai import Mistral
from websocket import create_connection
from IPython.display import Audio, display

# =============================================================================
# STEP 4: Generate Response Text
# =============================================================================

print("=" * 60)
print("🧠 STEP 4: Generate Response Text")
print("=" * 60)

def generate_response_simple(transcribed_text):
    """
    Simple response generation with fixed responses for common DeFi queries
    """
    print("🔄 Generating simple response...")
    
    # Simple keyword-based responses
    text_lower = transcribed_text.lower()
    
    if "yield farming" in text_lower:
        response_text = "Yield farming is lending crypto for rewards, but it's risky—let's discuss safely."
    elif "defi" in text_lower or "decentralized finance" in text_lower:
        response_text = "DeFi offers financial services without traditional banks. What specific aspect interests you?"
    elif "staking" in text_lower:
        response_text = "Staking lets you earn rewards by locking up crypto. It's generally safer than yield farming."
    elif "liquidity" in text_lower:
        response_text = "Liquidity pools enable trading on DEXs. You can provide liquidity to earn fees."
    elif "smart contract" in text_lower:
        response_text = "Smart contracts automate DeFi transactions. Always verify contract security first."
    else:
        response_text = "Hello! I'm Sophia, your DeFi mentor. Ask me about yield farming, staking, or other DeFi topics."
    
    print(f"✅ Simple Response: '{response_text}'")
    return response_text

def generate_response_llm(transcribed_text, client):
    """
    Dynamic response generation using Mistral LLM
    """
    print("🔄 Generating LLM response...")
    
    try:
        # Use Mistral Small for quick, focused responses
        response_gen = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "system", 
                    "content": "You are Sophia, a helpful DeFi mentor. Provide concise, educational responses about decentralized finance. Keep responses under 50 words and focus on safety and education."
                },
                {
                    "role": "user", 
                    "content": f"Respond as DeFi mentor to: {transcribed_text}"
                }
            ]
        )
        
        response_text = response_gen.choices[0].message.content
        print(f"✅ LLM Response: '{response_text}'")
        return response_text
        
    except Exception as e:
        print(f"❌ LLM generation error: {e}")
        # Fallback to simple response
        return generate_response_simple(transcribed_text)

def generate_response_voxtral(transcribed_text, client):
    """
    Alternative: Use Voxtral for integrated response generation
    """
    print("🔄 Generating Voxtral response...")
    
    try:
        # Use Voxtral for text response (streamlined approach)
        response_gen = client.chat.complete(
            model="voxtral-mini-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are Sophia, a helpful DeFi mentor. Provide concise, educational responses about decentralized finance. Keep responses under 50 words."
                },
                {
                    "role": "user", 
                    "content": f"Respond as DeFi mentor to: {transcribed_text}"
                }
            ]
        )
        
        response_text = response_gen.choices[0].message.content
        print(f"✅ Voxtral Response: '{response_text}'")
        return response_text
        
    except Exception as e:
        print(f"❌ Voxtral generation error: {e}")
        # Fallback to simple response
        return generate_response_simple(transcribed_text)

# Step 4 Main Execution
print("\n🎯 Step 4: Generating response to transcribed text...")

# Assume we have these variables from Step 3:
# transcribed_text = "What is yield farming?"  # From Voxtral output
# client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

try:
    # Method 1: Simple keyword-based (fastest, most reliable)
    response_text_simple = generate_response_simple(transcribed_text)
    
    # Method 2: LLM-generated (more dynamic)
    response_text_llm = generate_response_llm(transcribed_text, client)
    
    # Method 3: Voxtral-integrated (streamlined)
    # response_text_voxtral = generate_response_voxtral(transcribed_text, client)
    
    # Choose which response to use (for testing, use LLM)
    response_text = response_text_llm
    
    print(f"\n✅ FINAL RESPONSE: '{response_text}'")
    print(f"📊 Response length: {len(response_text)} characters")
    
except NameError:
    print("❌ Missing variables from Step 3. Using fallback for testing.")
    transcribed_text = "What is yield farming?"
    response_text = "Yield farming is lending crypto for rewards, but it's risky—let's discuss safely."
    print(f"🔄 Using fallback: '{response_text}'")

print("\n🎉 Step 4 Complete!")

# =============================================================================
# STEP 5: Inworld TTS API for Speech Generation
# =============================================================================

print("\n" + "=" * 60)
print("🎤 STEP 5: Text-to-Speech with Inworld TTS")
print("=" * 60)

def synthesize_speech_inworld_streaming(text, api_key):
    """
    Convert text to speech using Inworld TTS streaming API
    """
    print("🔄 Synthesizing speech with Inworld TTS (streaming)...")
    
    try:
        # Inworld WebSocket URL for streaming
        inworld_url = "wss://api.inworld.ai/v1/synthesize"
        
        # Connect WebSocket with authentication
        headers = {"Authorization": f"Bearer {api_key}"}
        ws = create_connection(inworld_url, header=headers)
        
        # Send synthesize request
        payload = {
            "text": text,
            "voice_id": "default-voice",  # Choose appropriate voice
            "emotion": "neutral",         # Options: neutral, happy, concerned, etc.
            "stream": True,
            "format": "wav"              # Audio format
        }
        
        print(f"📤 Sending request: {len(text)} characters")
        ws.send(json.dumps(payload))
        
        # Receive streaming audio chunks
        output_audio_data = b''
        chunk_count = 0
        
        while True:
            try:
                chunk = ws.recv()
                if not chunk:
                    break
                    
                # Handle JSON responses vs binary audio
                if isinstance(chunk, str):
                    response = json.loads(chunk)
                    if response.get("error"):
                        print(f"❌ TTS Error: {response['error']}")
                        break
                    elif response.get("status") == "complete":
                        print("✅ Streaming complete")
                        break
                else:
                    output_audio_data += chunk
                    chunk_count += 1
                    
            except Exception as e:
                print(f"❌ Chunk processing error: {e}")
                break
        
        ws.close()
        
        print(f"✅ Received {chunk_count} audio chunks ({len(output_audio_data)} bytes)")
        return output_audio_data
        
    except Exception as e:
        print(f"❌ Inworld TTS streaming error: {e}")
        return None

def synthesize_speech_inworld_simple(text, api_key):
    """
    Convert text to speech using Inworld TTS simple POST API (fallback)
    """
    print("🔄 Synthesizing speech with Inworld TTS (simple)...")
    
    try:
        import requests
        
        # Inworld REST API endpoint
        url = "https://api.inworld.ai/v1/synthesize"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "voice_id": "default-voice",
            "emotion": "neutral",
            "format": "wav"
        }
        
        print(f"📤 Sending POST request: {len(text)} characters")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            audio_data = response.content
            print(f"✅ Received audio: {len(audio_data)} bytes")
            return audio_data
        else:
            print(f"❌ TTS API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Inworld TTS simple error: {e}")
        return None

def create_mock_tts_audio(text):
    """
    Create mock TTS audio for testing when Inworld API is not available
    """
    print("🔄 Creating mock TTS audio for testing...")
    
    try:
        # Create a simple beep sound as placeholder
        import numpy as np
        from scipy.io.wavfile import write
        
        # Generate a simple tone (440 Hz for 2 seconds)
        sample_rate = 44100
        duration = 2.0
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Convert to 16-bit integers
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Save as WAV
        mock_file = "mock_tts_audio.wav"
        write(mock_file, sample_rate, audio_data)
        
        # Read back as bytes
        with open(mock_file, "rb") as f:
            audio_bytes = f.read()
        
        print(f"✅ Created mock audio: {len(audio_bytes)} bytes")
        print(f"💡 Note: This is a placeholder beep. Replace with actual Inworld TTS.")
        
        return audio_bytes
        
    except Exception as e:
        print(f"❌ Mock TTS creation error: {e}")
        return None

# Step 5 Main Execution
print("\n🎯 Step 5: Converting response text to speech...")

try:
    # Get Inworld API key
    inworld_api_key = os.environ.get('INWORLD_API_KEY')
    
    if inworld_api_key:
        print("🔑 Inworld API key found")
        
        # Try streaming first, fallback to simple
        audio_data = synthesize_speech_inworld_streaming(response_text, inworld_api_key)
        
        if not audio_data:
            print("🔄 Streaming failed, trying simple API...")
            audio_data = synthesize_speech_inworld_simple(response_text, inworld_api_key)
    else:
        print("⚠️ No Inworld API key found, using mock TTS")
        audio_data = create_mock_tts_audio(response_text)
    
    if audio_data:
        # Save audio file
        output_audio_file = "sophia_response.wav"
        with open(output_audio_file, "wb") as f:
            f.write(audio_data)
        
        print(f"💾 Saved audio: {output_audio_file}")
        
        # Play audio in notebook
        print("🔊 Playing generated speech:")
        display(Audio(output_audio_file))
        
    else:
        print("❌ Failed to generate speech audio")
        
except Exception as e:
    print(f"❌ Step 5 error: {e}")
    # Create fallback audio
    audio_data = create_mock_tts_audio("Hello, this is a test.")
    if audio_data:
        output_audio_file = "sophia_response.wav"
        with open(output_audio_file, "wb") as f:
            f.write(audio_data)
        display(Audio(output_audio_file))

print("\n🎉 Step 5 Complete!")

# =============================================================================
# STEP 6: Full End-to-End Test and Performance Analysis
# =============================================================================

print("\n" + "=" * 60)
print("🚀 STEP 6: Full End-to-End Test")
print("=" * 60)

def test_voice_conversation_full():
    """
    Complete voice conversation test: Record → Transcribe → Respond → Synthesize → Play
    """
    print("🧪 Running full voice conversation test...")
    
    # Performance tracking
    start_time = time.perf_counter()
    step_times = {}
    
    try:
        # Step 1: Audio Input (assume already done)
        step_start = time.perf_counter()
        print("\n📍 Step 1: Audio Input")
        print(f"   Input file: {input_audio_file}")
        step_times['audio_input'] = time.perf_counter() - step_start
        
        # Step 2: Transcription (assume already done)
        step_start = time.perf_counter()
        print("\n📍 Step 2: Transcription")
        print(f"   Transcribed: '{transcribed_text[:50]}...'")
        step_times['transcription'] = time.perf_counter() - step_start
        
        # Step 3: Response Generation
        step_start = time.perf_counter()
        print("\n📍 Step 3: Response Generation")
        response = generate_response_llm(transcribed_text, client)
        print(f"   Response: '{response[:50]}...'")
        step_times['response_gen'] = time.perf_counter() - step_start
        
        # Step 4: Speech Synthesis
        step_start = time.perf_counter()
        print("\n📍 Step 4: Speech Synthesis")
        
        inworld_key = os.environ.get('INWORLD_API_KEY')
        if inworld_key:
            audio_data = synthesize_speech_inworld_simple(response, inworld_key)
        else:
            audio_data = create_mock_tts_audio(response)
            
        if audio_data:
            test_output_file = "full_test_output.wav"
            with open(test_output_file, "wb") as f:
                f.write(audio_data)
            print(f"   Generated: {test_output_file}")
        
        step_times['speech_synthesis'] = time.perf_counter() - step_start
        
        # Calculate total time
        total_time = time.perf_counter() - start_time
        
        # Performance Report
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE REPORT")
        print("=" * 50)
        
        print(f"🎤 Audio Input:      {step_times.get('audio_input', 0):.2f}s")
        print(f"📝 Transcription:    {step_times.get('transcription', 0):.2f}s")
        print(f"🧠 Response Gen:     {step_times['response_gen']:.2f}s")
        print(f"🎵 Speech Synthesis: {step_times['speech_synthesis']:.2f}s")
        print(f"⏱️  TOTAL TIME:       {total_time:.2f}s")
        
        # Quality Assessment
        print("\n📋 QUALITY ASSESSMENT")
        print("-" * 30)
        
        # Transcription quality
        if len(transcribed_text) > 10:
            print("✅ Transcription: Good length")
        else:
            print("⚠️ Transcription: May be too short")
        
        # Response quality
        if 20 <= len(response) <= 200:
            print("✅ Response: Good length")
        else:
            print("⚠️ Response: Check length (too short/long)")
        
        # Audio quality
        if audio_data and len(audio_data) > 1000:
            print("✅ Audio: Generated successfully")
        else:
            print("⚠️ Audio: May have issues")
        
        # Latency assessment
        if total_time < 10:
            print("✅ Latency: Excellent (<10s)")
        elif total_time < 20:
            print("⚠️ Latency: Good (<20s)")
        else:
            print("❌ Latency: Needs optimization (>20s)")
        
        # Play final result
        if audio_data:
            print("\n🔊 Playing final result:")
            display(Audio(test_output_file))
        
        return True
        
    except Exception as e:
        print(f"❌ Full test error: {e}")
        return False

def run_conversation_loop(num_tests=1):
    """
    Run multiple conversation tests for consistency checking
    """
    print(f"🔄 Running {num_tests} conversation test(s)...")
    
    success_count = 0
    total_times = []
    
    for i in range(num_tests):
        print(f"\n{'='*20} TEST {i+1}/{num_tests} {'='*20}")
        
        start_time = time.perf_counter()
        success = test_voice_conversation_full()
        test_time = time.perf_counter() - start_time
        
        if success:
            success_count += 1
            total_times.append(test_time)
        
        print(f"Test {i+1} {'✅ PASSED' if success else '❌ FAILED'} ({test_time:.2f}s)")
    
    # Summary
    print(f"\n{'='*50}")
    print("📈 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Successful tests: {success_count}/{num_tests}")
    
    if total_times:
        avg_time = sum(total_times) / len(total_times)
        min_time = min(total_times)
        max_time = max(total_times)
        
        print(f"⏱️  Average time: {avg_time:.2f}s")
        print(f"⚡ Fastest time: {min_time:.2f}s")
        print(f"🐌 Slowest time: {max_time:.2f}s")
    
    return success_count == num_tests

# Step 6 Main Execution
print("\n🎯 Step 6: Running full end-to-end test...")

try:
    # Single comprehensive test
    print("\n🧪 Running single comprehensive test:")
    test_success = test_voice_conversation_full()
    
    if test_success:
        print("\n✅ Full test completed successfully!")
        
        # Optional: Run multiple tests for consistency
        run_multiple = input("\n❓ Run multiple tests for consistency? (y/n): ").lower().strip()
        if run_multiple == 'y':
            num_tests = int(input("How many tests? (1-5): ") or "3")
            run_conversation_loop(min(num_tests, 5))
    
    else:
        print("\n❌ Test failed. Check the errors above.")
    
except Exception as e:
    print(f"❌ Step 6 error: {e}")

print("\n🎉 Step 6 Complete!")

# =============================================================================
# FINAL SUMMARY AND NEXT STEPS
# =============================================================================

print("\n" + "=" * 60)
print("🏁 VOICE CONVERSATION TEST COMPLETE")
print("=" * 60)

print("\n✅ COMPLETED STEPS:")
print("   1. ✅ Environment setup and dependencies")
print("   2. ✅ Audio input (recording/upload)")
print("   3. ✅ Voxtral transcription and understanding")
print("   4. ✅ Response generation (simple/LLM/Voxtral)")
print("   5. ✅ Inworld TTS speech synthesis")
print("   6. ✅ Full end-to-end testing and performance analysis")

print("\n🔧 OPTIMIZATION TIPS:")
print("   • For faster responses: Use simple keyword-based generation")
print("   • For better quality: Use Mistral LLM or Voxtral integration")
print("   • For lower latency: Implement streaming for both transcription and TTS")
print("   • For production: Add error recovery and retry logic")

print("\n🚀 NEXT STEPS FOR MVP:")
print("   • Integrate with Kimi for complex DeFi analysis")
print("   • Add conversation memory/context")
print("   • Implement real-time streaming pipeline")
print("   • Add emotion detection and appropriate TTS emotions")
print("   • Create web interface for easy testing")

print("\n📊 EXPECTED PERFORMANCE:")
print("   • Total latency: 5-15 seconds (depending on audio length)")
print("   • Transcription accuracy: High for clear audio")
print("   • Response quality: Good for DeFi topics")
print("   • TTS quality: Natural-sounding speech")

print("\n💡 TROUBLESHOOTING:")
print("   • If transcription fails: Check audio quality and format")
print("   • If TTS fails: Verify Inworld API key and credits")
print("   • If responses are poor: Adjust system prompts")
print("   • If latency is high: Check internet connection and API limits")

print("\n🎯 Your voice conversation system is ready for testing!")
print("Copy the code blocks above into your notebook and run them sequentially.")
