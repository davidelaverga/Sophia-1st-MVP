# Sophia DeFi Frontend

A crypto-themed web interface for the Sophia DeFi voice assistant.

## Features

- **Voice Chat**: Hold-to-talk voice recording with real-time transcription
- **Text Chat**: Type-based conversations with the DeFi agent
- **Crypto Branding**: Gold/purple/cyan theme with animated UI elements
- **Emotion Display**: Shows detected emotions from both user and Sophia
- **Audio Playback**: Listen to Sophia's synthesized voice responses
- **Session Memory**: Maintains conversation context across interactions
- **Quick Actions**: Pre-configured DeFi questions for easy access
- **Responsive Design**: Works on desktop and mobile devices

## Setup

1. Ensure the Sophia backend is running on `http://localhost:8000`
2. Open `index.html` in a web browser
3. Configure your API key in settings (⚙️ button)
4. Start chatting with Sophia about DeFi!

## Usage

### Voice Interaction
- Hold down the "Hold to Talk" button to record
- Release to send the audio to Sophia
- Listen to Sophia's voice response automatically

### Text Interaction
- Type your message in the text input
- Press Enter or click the ⚡ button to send
- Use quick action buttons for common DeFi questions

### Settings
- Click the ⚙️ button to access settings
- Enter your API key (required for authentication)
- Modify the API URL if running backend elsewhere

## File Structure

- `index.html` - Main HTML structure
- `styles.css` - Crypto-themed CSS styling
- `script.js` - JavaScript functionality and API integration

## API Integration

Connects to Sophia backend endpoints:
- `POST /defi-chat` - Voice conversations with full LangGraph pipeline
- `POST /text-chat` - Text-only conversations  
- `GET /health` - API health monitoring
- `GET /sessions/{id}` - Session memory retrieval

## Browser Requirements

- Modern browser with Web Audio API support
- Microphone access for voice features
- JavaScript enabled