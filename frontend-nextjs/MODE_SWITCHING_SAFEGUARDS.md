# Mode Switching Safeguards Implementation

**Status:** ✅ COMPLETE  
**Date:** November 30, 2025  
**Architecture:** CLEAN Architecture (Domain → Presentation → UI)

---

## 📋 Overview

Implemented robust mode switching safeguards to prevent data loss and race conditions when users switch between Chat and Voice modes. The implementation follows CLEAN Architecture principles with clear separation of concerns:

1. **Domain Layer** (`mode-switching.ts`) - Pure business logic
2. **Presentation Layer** (`useModeSwitch.ts`) - React hook bridging domain and UI
3. **UI Layer** (Components) - User interface with validation

---

## 🏗️ Architecture

### Layer 1: Domain Logic (`app/lib/mode-switching.ts`)

**Purpose:** Pure business logic with zero dependencies on React, stores, or UI.

**Key Functions:**
- `canSwitchToVoice(state)` - Validates switching from chat to voice
- `canSwitchToChat(state)` - Validates switching from voice to chat
- `canAutoSwitchMode(state)` - Validates automatic mode switching
- `getBlockedSwitchMessage(reason)` - User-friendly error messages

**Business Rules:**
1. ❌ Cannot switch to voice while chat is locked (Sophia responding)
2. ❌ Cannot switch to chat while voice is recording
3. ❌ Cannot switch to chat while voice is processing
4. ❌ Cannot switch to chat while voice is playing audio
5. ❌ Auto-switch blocked if ANY operation is active

**Types:**
```typescript
export interface AppOperationState {
  isChatLocked: boolean;
  isVoiceActive: boolean;
  isVoiceRecording: boolean;
  isVoicePlaying: boolean;
  isModalOpen: boolean;
}

export type BlockReason = 
  | "chat_locked"
  | "voice_recording"
  | "voice_processing"
  | "voice_playing"
  | "modal_open"
  | "none";
```

---

### Layer 2: Presentation Hook (`app/hooks/useModeSwitch.ts`)

**Purpose:** Bridge domain logic with React state management.

**Returns:**
```typescript
interface UseModeSwitch {
  canSwitchToVoice: ModeSwitchValidation;
  canSwitchToChat: ModeSwitchValidation;
  canAutoSwitch: boolean;
  switchToVoice: () => void;
  switchToChat: () => void;
  operationState: AppOperationState;
}
```

**Features:**
- Observes `useChatStore` (isLocked)
- Observes `useVoiceLoop` (voiceStage)
- Calls domain validation functions
- Provides validated switch handlers
- Triggers `onBlocked` callback when switch is denied

**Usage Example:**
```tsx
const { canSwitchToVoice, switchToVoice } = useModeSwitch({
  onBlocked: (message) => {
    showToast({ message, type: "warning" })
  }
})

<button 
  onClick={switchToVoice}
  disabled={!canSwitchToVoice.canSwitch}
  title={canSwitchToVoice.message}
>
  Switch to Voice
</button>
```

---

### Layer 3: UI Components

#### `VoiceCollapsed.tsx`
- Uses `useModeSwitch()` hook
- Disabled when `!canSwitchToVoice.canSwitch`
- Shows tooltip: `canSwitchToVoice.message`
- Toast feedback on blocked switch: "Espera a que termine el mensaje actual"

#### `ChatCollapsed.tsx`
- Uses `useModeSwitch()` hook
- Disabled when `!canSwitchToChat.canSwitch`
- Shows tooltip: `canSwitchToChat.message`
- Toast feedback on blocked switch: "Termina de grabar primero" / "Espera a que termine de hablar"

#### `ConversationView.tsx`
- Auto-switch now checks `canAutoSwitch` before proceeding
- Prevents interruptions during:
  - Chat locked (Sophia responding)
  - Voice recording
  - Voice playback
  - Modal open

---

## 🔒 Protection Scenarios

### Scenario 1: User tries to switch to voice while Sophia is responding

**Before:**
```tsx
// ❌ Immediate switch, message response interrupted
setMode("voice")
setManualOverride(true)
```

**After:**
```tsx
// ✅ Blocked with feedback
if (isChatLocked) {
  showToast("Espera a que termine el mensaje actual")
  return // Switch denied
}
```

---

### Scenario 2: User tries to switch to chat while recording

**Before:**
```tsx
// ❌ Immediate switch, recording lost
setMode("text")
setManualOverride(true)
```

**After:**
```tsx
// ✅ Blocked with feedback
if (voiceStage === "listening") {
  showToast("Termina de grabar primero")
  return // Switch denied
}
```

---

### Scenario 3: Auto-switch interrupts active operation

**Before:**
```tsx
// ❌ Auto-switch can interrupt user recording
if (composerHasFocus) {
  setMode("text") // Interrupts voice!
}
```

**After:**
```tsx
// ✅ Auto-switch respects operations
if (!canAutoSwitch) return // Blocked

if (composerHasFocus) {
  setMode("text") // Safe
}
```

---

## 🎯 User Experience

### Visual Feedback

1. **Disabled Button State:**
   ```css
   disabled:opacity-50 
   disabled:cursor-not-allowed
   disabled:hover:shadow-soft
   ```

2. **Tooltip Messages:**
   - "Espera a que termine el mensaje actual"
   - "Termina de grabar primero"
   - "Espera a que termine de procesar"
   - "Espera a que termine de hablar"

3. **Toast Notifications:**
   - Uses existing `useUsageLimitStore.showToast()`
   - Appears when user clicks disabled button
   - Auto-dismisses after 3 seconds

---

## 🧪 Testing Checklist

### Manual Tests

- [ ] **Chat → Voice (Blocked):**
  1. Send message in chat
  2. While Sophia is streaming response, click "Switch to voice"
  3. ✅ Button is disabled (opacity 50%)
  4. ✅ Hover shows tooltip: "Espera a que termine el mensaje actual"
  5. ✅ Click shows toast notification

- [ ] **Voice → Chat (Recording):**
  1. Start voice recording
  2. While recording, click "Switch to chat"
  3. ✅ Button is disabled
  4. ✅ Tooltip: "Termina de grabar primero"
  5. ✅ Toast appears on click attempt

- [ ] **Voice → Chat (Playing):**
  1. Ask question via voice
  2. While Sophia is speaking, click "Switch to chat"
  3. ✅ Button is disabled
  4. ✅ Tooltip: "Espera a que termine de hablar"

- [ ] **Auto-Switch Respects Operations:**
  1. Start voice recording
  2. Focus composer (would normally auto-switch to text)
  3. ✅ Stays in voice mode (doesn't interrupt)

### Edge Cases

- [ ] Rapid clicking disabled button → Only one toast shown
- [ ] Switch allowed after operation completes
- [ ] Manual override still works (30s timeout)
- [ ] No console errors during mode transitions

---

## 📊 Impact

### Files Changed: 5
1. ✅ `app/lib/mode-switching.ts` (NEW - 162 lines)
2. ✅ `app/hooks/useModeSwitch.ts` (NEW - 141 lines)
3. ✅ `app/components/VoiceCollapsed.tsx` (MODIFIED - +15 lines)
4. ✅ `app/components/ChatCollapsed.tsx` (MODIFIED - +15 lines)
5. ✅ `app/components/ConversationView.tsx` (MODIFIED - +4 lines)

### Total Lines: ~337 lines added

### Zero TypeScript Errors: ✅

---

## 🚀 What's Next

### Optional Enhancements (P3 - Post-Deploy)

1. **Confirmation Dialogs:**
   - "Cancel recording and switch to chat?"
   - "Interrupt response and switch to voice?"

2. **Advanced Feedback:**
   - Progress indicator during operations
   - Estimated time until switch is available

3. **Analytics:**
   - Track how often switches are blocked
   - Identify UX friction points

4. **Unit Tests:**
   ```typescript
   // app/lib/__tests__/mode-switching.test.ts
   describe("canSwitchToVoice", () => {
     it("blocks when chat is locked", () => {
       const state = { isChatLocked: true, ... }
       expect(canSwitchToVoice(state).canSwitch).toBe(false)
     })
   })
   ```

---

## 🎓 CLEAN Architecture Benefits

### ✅ Testability
- Domain logic is pure functions (easy to unit test)
- No mocking needed for business rules

### ✅ Maintainability
- Business rules in one place (`mode-switching.ts`)
- Changes to rules don't affect UI

### ✅ Flexibility
- Can replace React hook with Vue/Angular/Svelte wrapper
- Domain logic remains unchanged

### ✅ Clarity
- Clear separation: Domain → Presentation → UI
- Easy to understand and reason about

---

## 📝 Developer Notes

### Adding New Block Reasons

1. Add to `BlockReason` type in `mode-switching.ts`
2. Add case in `getBlockedSwitchMessage()`
3. Add validation logic in `canSwitchToVoice/Chat()`
4. Update `AppOperationState` if needed

### Example:
```typescript
// 1. Add type
export type BlockReason = ... | "ai_thinking"

// 2. Add message
case "ai_thinking":
  return "Espera a que Sophia piense"

// 3. Add validation
if (state.isAiThinking) {
  return {
    canSwitch: false,
    reason: "ai_thinking",
    message: "Espera a que Sophia piense"
  }
}
```

---

## ✨ Summary

**Problem:** Users could lose data by switching modes during operations.

**Solution:** CLEAN Architecture mode switching safeguards with:
- ✅ Domain-driven validation logic
- ✅ Reactive presentation hook
- ✅ Disabled UI with tooltips
- ✅ Toast notifications for feedback
- ✅ Auto-switch protection

**Result:** Seamless, data-safe mode transitions. 🎉
