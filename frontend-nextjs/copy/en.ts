export const copy = {
  brand: {
    name: "Sophia",
    tagline: "Voice-first emotional companion",
    initial: "S",
  },
  presence: {
    listening: "Listening",
    thinking: "Thinking",
    reflecting: "Reflecting",
    speaking: "Speaking",
    resting: "Resting",
  },
  shell: {
    settingsPlaceholderTitle: "Settings arrive in Part 7",
    settingsPlaceholderBody: "We are building a gentle panel for presets, presence, and privacy toggles. It will appear here soon.",
    closeSettings: "Close",
  },
  settings: {
    title: "Settings",
  },
  auth: {
    title: "Sophia",
    subtitle: "A calm, emotionally-aware companion.",
    button: "Continue with Discord",
    loading: "Opening a gentle space...",
    errors: {
      discord: "Discord sign-in failed. Please try again.",
      unexpected: "We could not contact Discord. Please try again shortly.",
    },
  },
  header: {
    subtitle: "Voice-first emotional companion",
  },
  gate: {
    title: "Consent required",
    body: "Please accept our data processing consent before your first session.",
    cta: "Review consent",
  },
  home: {
    placeholder: "Conversation view mounts here next. For now, we have the design tokens and shell in place.",
    hero: {
      heading: "Welcome back",
      status: "Sophia is present",
      body: "I hold space for gentle conversations about how you feel. Take a breath and start whenever you are ready.",
      statusIcon: "✨",
    },
    rituals: {
      title: "Gentle rituals",
      items: [
        {
          id: "breath",
          emoji: "🌬️",
          title: "Breathing check-in",
          description: "A two-minute pause that softens your nervous system.",
        },
        {
          id: "gratitude",
          emoji: "✨",
          title: "Gratitude whisper",
          description: "Name one small kindness you noticed today.",
        },
      ],
    },
    presence: {
      title: "Presence snapshot",
      metrics: [
        { id: "response", label: "Avg response time", value: "approx. 2.3s" },
        { id: "listening", label: "Listening focus", value: "Deep" },
      ],
    },
    cards: [
      {
        id: "grounding",
        title: "Grounding prompt",
        description: "Ease into the moment before you speak.",
      },
      {
        id: "journal",
        title: "Tiny reflection",
        description: "Capture the feeling you want to remember later.",
      },
    ],
  },
  liveCall: {
    title: "Live voice space",
    description: "Start a real-time call. Sophia listens the moment you begin speaking.",
    start: "Begin call",
    end: "End call",
    states: {
      live: "Live (mic on)",
      connected: "Connected",
      disconnected: "Disconnected",
    },
    partialLabel: "Sophia",
    finalLabel: "Final reply",
    tip: "Tip: interrupt whenever you need. Sophia stops speaking instantly.",
  },
  chat: {
    placeholder: "Share what you are feeling or noticing...",
    send: "Send",
    sending: "Sending...",
    loading: "Sophia is holding space for your words...",
    audioButton: "Play voice reply",
    quickStartTitle: "Need a place to begin?",
    quickPrompts: [
      { id: "overwhelmed", emoji: "😵‍💫", label: "I'm feeling overwhelmed" },
      { id: "breath", emoji: "🌬️", label: "Guide me through a calm breath" },
      { id: "gratitude", emoji: "🌱", label: "Help me notice something kind" },
    ],
    transcriptLabel: "Sophia",
    error: "Something felt unclear. Could you try again?",
  },
  voiceRecorder: {
    title: "Voice reflections",
    subtitle: "Speak naturally with Sophia",
    readyTitle: "Ready to listen",
    readyBody: "Tap the microphone and share how you are really doing.",
    recordingTitle: "Listening...",
    recordingBody: "Take your time. Silence is welcome too.",
    timerLabel: "Recording time",
    recordingBadge: "Recording",
    tipsTitle: "Tips",
    highlights: [
      { id: "insight", emoji: "🎧", label: "Gentle insights" },
      { id: "presence", emoji: "⏱️", label: "Real-time presence" },
      { id: "voice", emoji: "🔊", label: "Soft voice replies" },
    ],
    tips: [
      "Speak clearly and at a steady pace.",
      "Share feelings, sensations, or small observations.",
      "Pause whenever you need. Sophia keeps listening.",
    ],
    errors: {
      micDenied: "Microphone access was denied. Please allow microphone permissions.",
      noAudio: "No audio captured. Please try recording again.",
      network: "Voice message failed. Please try again.",
    },
    buttons: {
      start: "Start recording",
      stop: "Stop",
    },
  },
  consentModal: {
    title: "Consent required",
    intro: "Sophia gently records your voice and transcripts to learn how to support you.",
    noticeTitle: "Data processing notice",
    noticeBody: "Your conversations are encrypted in transit and processed only to help Sophia grow more empathetic.",
    whatTitle: "What we collect",
    whatItems: [
      "Voice recordings for transcription and emotion sensing",
      "Chat messages and AI responses",
      "Usage patterns and session data",
      "Discord profile basics (username and avatar)",
    ],
    howTitle: "How it helps",
    howItems: [
      "Provide personalized emotional support",
      "Improve Sophia's response quality",
      "Monitor safety and consent requirements",
      "Share anonymous insights with the community",
    ],
    retention: "We hash your consent record with timestamp and IP. You can export or delete all data at any time.",
    errors: {
      save: "Consent could not be saved. You can continue, but we may ask again soon.",
      network: "Network error while saving consent. We will still let you continue.",
    },
    buttons: {
      cancel: "Cancel",
      accept: "I agree",
      saving: "Saving...",
    },
  },
  reflection: {
    promptTitle: "Would you like to capture this moment?",
    promptBody: "Choose the sentence that resonates most right now.",
    savePrivate: "Save privately",
    shareDiscord: "Share with the community",
    dismiss: "Not now",
  },
  errors: {
    generic: "Something felt off. Please try again.",
  },
} as const
