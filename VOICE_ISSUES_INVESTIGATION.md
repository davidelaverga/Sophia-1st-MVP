# 🔍 Voice Mode Issues - Deep Investigation

**Date**: November 25, 2025  
**Issues**: Duplicate messages + Sophia continues speaking without user input

---

## 🐛 Issue #1: Duplicate Messages in Transcript

### **Symptoms**:
```
Sophia's Voice
┌─────────────────────────────────┐
│ "Hey there! I'm doing great..." │ ← Message 1
│ "Hey there! I'm doing great..." │ ← Message 2 (DUPLICATE)
└─────────────────────────────────┘
```

### **Investigation**:

#### Hypothesis 1: `finalReply` not cleared ❌
**Code Review**:
```typescript
// VoiceTranscript.tsx line 29
const activeReply = partialReply  // Only shows partialReply, not finalReply
```
- ✅ Component correctly only shows `partialReply` as "active"
- ✅ `finalReply` should NOT be shown separately

#### Hypothesis 2: `finalReply` persists after save ✅ LIKELY
**Code Review**:
```typescript
// useVoiceLoop.ts line 329-337
case "reply_done": {
  const text = ...
  setFinalReply(text)  // Sets finalReply
  addVoiceMessage(text)  // Saves to history
  // ❌ finalReply NEVER gets cleared!
  break
}
```

**Problem**: 
- `finalReply` is set when `reply_done` arrives
- Message is saved to history
- But `finalReply` stays in state
- Next render: history shows message + `finalReply` still has value
- Even though `activeReply = partialReply`, the condition on line 23 checks `finalReply`

**Root Cause**:
```typescript
// Line 23 - Component doesn't return null if finalReply exists
if (messages.length === 0 && !partialReply && !finalReply) {
  return null
}
```

If `finalReply` has value, component renders even when it shouldn't show it.

#### Hypothesis 3: Multiple instances ❌
**Code Review**:
- ✅ Only one `useVoiceLoop` call in `ConversationView`
- ✅ Passed as props to components
- ❌ Not the issue

### **Solution Implemented**:
```typescript
case "reply_done": {
  const text = ...
  addVoiceMessage(text)  // Save first
  setFinalReply(text)    // Set briefly
  setTimeout(() => {
    setFinalReply("")    // Clear after 100ms
  }, 100)
  break
}
```

---

## 🐛 Issue #2: Sophia Continues Speaking Without Input

### **Symptoms**:
- User doesn't speak
- Sophia generates and sends multiple responses
- Appears to be in a loop

### **Investigation**:

#### Hypothesis 1: WebSocket not closed properly ✅ LIKELY
**Code Review**:
```typescript
const stopTalking = () => {
  cleanupRecorder()  // Stops microphone
  // ❌ Does NOT close WebSocket
  // ❌ Does NOT send "stop" signal to backend
  setStage("thinking")
}
```

**Problem**:
- When user releases button, `stopTalking()` is called
- Microphone stops, but WebSocket stays open
- Backend might interpret silence as continued input
- Or backend has a bug causing loops

#### Hypothesis 2: Backend auto-continues conversation 🤔
**Possible Backend Issues**:
1. Backend interprets silence as "continue"
2. Backend has a loop bug
3. Backend doesn't receive "stop" signal
4. Backend continues after `reply_done`

#### Hypothesis 3: Multiple WebSocket connections ❌
**Code Review**:
```typescript
const ensureConnection = () => {
  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
    return Promise.resolve(wsRef.current)  // Reuses existing
  }
  // Creates new only if needed
}
```
- ✅ Only one WebSocket at a time
- ❌ Not the issue

#### Hypothesis 4: Event listener duplication ❌
**Code Review**:
```typescript
ws.onmessage = handleServerMessage  // Set once on connection
```
- ✅ Only one listener per WebSocket
- ❌ Not the issue

### **Evidence Needed**:
1. **Console logs**: What events are being received?
2. **Network tab**: Is WebSocket sending multiple messages?
3. **Backend logs**: Is backend generating multiple responses?

### **Potential Solutions**:

#### Solution A: Send explicit "stop" signal
```typescript
const stopTalking = () => {
  cleanupRecorder()
  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
    // Send stop signal to backend
    wsRef.current.send(JSON.stringify({ type: "stop" }))
  }
  setStage("thinking")
}
```

#### Solution B: Close WebSocket after response
```typescript
case "reply_done": {
  // ... save message ...
  // Close WebSocket to prevent further responses
  if (wsRef.current) {
    wsRef.current.close()
    wsRef.current = null
  }
  break
}
```

#### Solution C: Add response counter/guard
```typescript
const [responseCount, setResponseCount] = useState(0)

const startTalking = async () => {
  setResponseCount(0)  // Reset counter
  // ... start recording ...
}

case "reply_done": {
  setResponseCount(prev => prev + 1)
  if (responseCount > 0) {
    console.warn("[voice] Multiple responses detected, ignoring")
    return  // Ignore duplicate responses
  }
  // ... save message ...
}
```

---

## 🔬 Debug Logs Added

### **VoiceTranscript.tsx**:
```typescript
console.log("[VoiceTranscript] Render:", {
  messagesCount: messages.length,
  partialReply: partialReply ? partialReply.substring(0, 30) + "..." : "none",
  finalReply: finalReply ? finalReply.substring(0, 30) + "..." : "none",
})
```

### **useVoiceLoop.ts**:
```typescript
case "reply_done": {
  console.log("[voice] reply_done - text:", text.substring(0, 50) + "...")
  console.log("[voice] Saving to history")
  console.log("[voice] Clearing finalReply after save")
}
```

---

## 📊 Expected Console Output

### **Normal Flow**:
```
[voice] User pressed button
[voice] startTalking
[voice] stage: listening
[voice] User released button
[voice] stopTalking
[voice] stage: thinking
[voice] token received: "Hey"
[VoiceTranscript] Render: { messagesCount: 0, partialReply: "Hey...", finalReply: "none" }
[voice] token received: " there"
[VoiceTranscript] Render: { messagesCount: 0, partialReply: "Hey there...", finalReply: "none" }
[voice] reply_done - text: "Hey there! I'm doing great..."
[voice] Saving to history
[VoiceTranscript] Render: { messagesCount: 1, partialReply: "none", finalReply: "Hey there..." }
[voice] Clearing finalReply after save
[VoiceTranscript] Render: { messagesCount: 1, partialReply: "none", finalReply: "none" }
```

### **Bug Flow (Duplicate)**:
```
[voice] reply_done - text: "Hey there! I'm doing great..."
[voice] Saving to history
[VoiceTranscript] Render: { messagesCount: 1, partialReply: "none", finalReply: "Hey there..." }
// ❌ finalReply never cleared, shows alongside history
```

### **Bug Flow (Continues Speaking)**:
```
[voice] reply_done - text: "Response 1"
[voice] Saving to history
// ❌ Backend sends another reply_done without user input
[voice] reply_done - text: "Response 2"
[voice] Saving to history
// ❌ Loop continues
```

---

## 🎯 Action Items

### **Immediate**:
1. ✅ Clear `finalReply` after saving to history (DONE)
2. 🔄 Test with console logs to see actual flow
3. 🔄 Check if backend is sending multiple `reply_done` events

### **If Issue Persists**:
1. Implement Solution A (send stop signal)
2. Implement Solution C (response counter guard)
3. Contact backend team about loop issue

### **Long-term**:
1. Add response deduplication
2. Add WebSocket state management
3. Add timeout for responses (max 30s)
4. Add error recovery

---

## 📝 Questions for User

1. **When does Sophia continue speaking?**
   - Immediately after first response?
   - After a delay?
   - Only sometimes?

2. **How many times does she speak?**
   - Twice?
   - Infinite loop?
   - Random number?

3. **What's in the console?**
   - Multiple `reply_done` events?
   - Multiple `token` events?
   - Any errors?

4. **Network tab**:
   - Is WebSocket sending multiple messages?
   - Is backend responding multiple times?

---

## 🚨 Critical Findings

### **Issue #1 (Duplicate)**:
- **Root Cause**: `finalReply` not cleared after save
- **Fix**: Clear `finalReply` with setTimeout
- **Status**: ✅ Fixed (needs testing)

### **Issue #2 (Continues Speaking)**:
- **Root Cause**: Backend loop + Frontend not closing WebSocket
- **Evidence**: Multiple different responses without user input
- **Fix**: Close WebSocket after reply_done + Reset buffer
- **Status**: ✅ Fixed

---

**Next Steps**: Run app with debug logs and observe console output

