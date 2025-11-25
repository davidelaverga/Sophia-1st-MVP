#!/usr/bin/env python3
"""
Test for Task #42805: Verify session_id is correctly returned in text chat
Tests both regular /text-chat and streaming /text-chat/stream endpoints
"""

import requests
import os
import json
import uuid
from typing import Dict, List, Any


# Configuration
BASE_URL = os.getenv("API_URL", "http://localhost:8000")
ACCESS_TOKEN_ENV = "SUPABASE_ACCESS_TOKEN"


class TextChatSessionIDTester:
    def __init__(self, base_url: str = BASE_URL, auth_token: str | None = None):
        self.base_url = base_url
        token = auth_token or os.getenv(ACCESS_TOKEN_ENV)
        if not token:
            raise ValueError(
                f"Missing Supabase access token. Provide a JWT via the '{ACCESS_TOKEN_ENV}' environment variable "
                "or pass an explicit auth_token to TextChatSessionIDTester."
            )
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_text_chat_regular_session_id(self):
        """Test that /text-chat returns session_id in response"""
        print("\n🔍 Testing /text-chat endpoint - session_id in response...")

        try:
            # Generate a new session_id
            test_session_id = str(uuid.uuid4())

            payload = {"message": "What is DeFi?", "session_id": test_session_id}

            response = requests.post(
                f"{self.base_url}/text-chat",
                json=payload,
                headers=self.headers,
                timeout=60,
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ FAIL: Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

            data = response.json()

            # Check if session_id is in response
            if "session_id" not in data:
                print("❌ FAIL: session_id not found in response")
                print(f"Response keys: {data.keys()}")
                return False

            # Check if session_id matches what we sent
            if data["session_id"] != test_session_id:
                print("❌ FAIL: session_id mismatch")
                print(f"  Expected: {test_session_id}")
                print(f"  Received: {data['session_id']}")
                return False

            print(f"✅ PASS: session_id correctly returned: {data['session_id']}")
            print(f"  Reply: {data.get('reply', 'N/A')[:100]}...")
            return True

        except Exception as e:
            print(f"❌ FAIL: Exception occurred: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_text_chat_regular_without_session_id(self):
        """Test that /text-chat generates session_id when not provided"""
        print("\n🔍 Testing /text-chat endpoint - auto-generated session_id...")

        try:
            payload = {
                "message": "What is DeFi?"
                # No session_id provided
            }

            response = requests.post(
                f"{self.base_url}/text-chat",
                json=payload,
                headers=self.headers,
                timeout=60,
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ FAIL: Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

            data = response.json()

            # Check if session_id is in response
            if "session_id" not in data:
                print("❌ FAIL: session_id not found in response")
                print(f"Response keys: {data.keys()}")
                return False

            # Check if session_id is a valid UUID
            try:
                uuid.UUID(data["session_id"])
                print(f"✅ PASS: session_id auto-generated: {data['session_id']}")
                return True
            except ValueError:
                print(f"❌ FAIL: session_id is not a valid UUID: {data['session_id']}")
                return False

        except Exception as e:
            print(f"❌ FAIL: Exception occurred: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_text_chat_stream_session_id(self):
        """Test that /text-chat/stream returns session_id in SSE events"""
        print("\n🔍 Testing /text-chat/stream endpoint - session_id in SSE events...")

        try:
            # Generate a new session_id
            test_session_id = str(uuid.uuid4())

            payload = {
                "message": "What is yield farming?",
                "session_id": test_session_id,
            }

            response = requests.post(
                f"{self.base_url}/text-chat/stream",
                json=payload,
                headers=self.headers,
                timeout=60,
                stream=True,
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ FAIL: Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

            # Parse SSE events
            events = self._parse_sse_events(response)

            # Check for events
            if not events:
                print("❌ FAIL: No SSE events received")
                return False

            print(f"Received {len(events)} SSE events")

            # Check for meta event with session_id
            meta_events = [e for e in events if e["event"] == "meta"]
            if not meta_events:
                print("❌ FAIL: No 'meta' event found")
                print(f"Available events: {[e['event'] for e in events]}")
                return False

            meta_data = meta_events[0]["data"]
            if "session_id" not in meta_data:
                print("❌ FAIL: session_id not found in 'meta' event")
                print(f"Meta data: {meta_data}")
                return False

            if meta_data["session_id"] != test_session_id:
                print("❌ FAIL: session_id mismatch in 'meta' event")
                print(f"  Expected: {test_session_id}")
                print(f"  Received: {meta_data['session_id']}")
                return False

            print(
                f"✅ PASS: 'meta' event has correct session_id: {meta_data['session_id']}"
            )

            # Check for reply_done event with session_id
            reply_done_events = [e for e in events if e["event"] == "reply_done"]
            if not reply_done_events:
                print("❌ FAIL: No 'reply_done' event found")
                return False

            reply_done_data = reply_done_events[0]["data"]
            if "session_id" not in reply_done_data:
                print("❌ FAIL: session_id not found in 'reply_done' event")
                print(f"Reply done data: {reply_done_data}")
                return False

            if reply_done_data["session_id"] != test_session_id:
                print("❌ FAIL: session_id mismatch in 'reply_done' event")
                print(f"  Expected: {test_session_id}")
                print(f"  Received: {reply_done_data['session_id']}")
                return False

            print("✅ PASS: 'reply_done' event has correct session_id")

            # Check for audio_url event with session_id
            audio_url_events = [e for e in events if e["event"] == "audio_url"]
            if audio_url_events:
                audio_url_data = audio_url_events[0]["data"]
                if "session_id" not in audio_url_data:
                    print("⚠️  WARNING: session_id not found in 'audio_url' event")
                    print(f"Audio URL data: {audio_url_data}")
                elif audio_url_data["session_id"] != test_session_id:
                    print("⚠️  WARNING: session_id mismatch in 'audio_url' event")
                    print(f"  Expected: {test_session_id}")
                    print(f"  Received: {audio_url_data['session_id']}")
                else:
                    print("✅ PASS: 'audio_url' event has correct session_id")

            return True

        except Exception as e:
            print(f"❌ FAIL: Exception occurred: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_text_chat_stream_without_session_id(self):
        """Test that /text-chat/stream generates session_id when not provided"""
        print("\n🔍 Testing /text-chat/stream endpoint - auto-generated session_id...")

        try:
            payload = {
                "message": "What is liquidity mining?"
                # No session_id provided
            }

            response = requests.post(
                f"{self.base_url}/text-chat/stream",
                json=payload,
                headers=self.headers,
                timeout=60,
                stream=True,
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ FAIL: Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

            # Parse SSE events
            events = self._parse_sse_events(response)

            # Check for meta event with session_id
            meta_events = [e for e in events if e["event"] == "meta"]
            if not meta_events:
                print("❌ FAIL: No 'meta' event found")
                return False

            meta_data = meta_events[0]["data"]
            if "session_id" not in meta_data:
                print("❌ FAIL: session_id not found in 'meta' event")
                return False

            # Check if session_id is a valid UUID
            try:
                uuid.UUID(meta_data["session_id"])
                print(f"✅ PASS: session_id auto-generated: {meta_data['session_id']}")
                return True
            except ValueError:
                print(
                    f"❌ FAIL: session_id is not a valid UUID: {meta_data['session_id']}"
                )
                return False

        except Exception as e:
            print(f"❌ FAIL: Exception occurred: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _parse_sse_events(self, response) -> List[Dict[str, Any]]:
        """Parse SSE events from streaming response"""
        events = []
        current_event = None
        current_data = []

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                # Empty line marks end of event
                if current_event and current_data:
                    data_str = "\n".join(current_data)
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = data_str
                    events.append({"event": current_event, "data": data})
                    current_event = None
                    current_data = []
                continue

            if line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                current_data.append(line[5:].strip())

        # Handle last event if exists
        if current_event and current_data:
            data_str = "\n".join(current_data)
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = data_str
            events.append({"event": current_event, "data": data})

        return events

    def run_all_tests(self):
        """Run all test cases"""
        print("=" * 80)
        print("Starting Text Chat Session ID Test Suite (Task #42805)")
        print(f"Testing server at: {self.base_url}")
        print("=" * 80)

        tests = [
            (
                "Regular /text-chat with session_id",
                self.test_text_chat_regular_session_id,
            ),
            (
                "Regular /text-chat without session_id",
                self.test_text_chat_regular_without_session_id,
            ),
            (
                "Streaming /text-chat/stream with session_id",
                self.test_text_chat_stream_session_id,
            ),
            (
                "Streaming /text-chat/stream without session_id",
                self.test_text_chat_stream_without_session_id,
            ),
        ]

        results = {}
        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed += 1
            except Exception as e:
                print(f"❌ Test '{test_name}' raised an exception: {e}")
                import traceback

                traceback.print_exc()
                results[test_name] = False

        print("\n" + "=" * 80)
        print("Test Results Summary")
        print("=" * 80)
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")

        print(f"\n📊 Total: {passed}/{total} tests passed")
        print("=" * 80)

        return passed == total


if __name__ == "__main__":
    import sys

    tester = TextChatSessionIDTester()
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)
