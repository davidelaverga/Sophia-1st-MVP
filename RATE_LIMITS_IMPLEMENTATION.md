# Rate Limits & Founding Supporter - Implementation Summary

**Fecha:** 22 de noviembre, 2025  
**Developer:** Luis (Frontend)  
**Feature:** Sistema de límites de uso y página de Founding Supporter

---

## 🎯 Objetivo Completado

Implementar un sistema completo de rate limits con un paywall suave y empático que invite a los usuarios a convertirse en "Founding Supporters" cuando alcancen sus límites diarios gratuitos.

---

## ✅ Lo Que Se Implementó

### 1. Tipos y Constantes TypeScript

**Archivo:** `frontend-nextjs/app/types/rate-limits.ts`

Definiciones de tipos para:
- `UsageLimitReason`: "voice" | "text" | "reflections"
- `PlanTier`: "FREE" | "FOUNDING_SUPPORTER"
- `UsageLimitError`: Contrato del backend para errores de límite
- `UsageLimitInfo`: Info simplificada para el modal
- `FOUNDING_PRICE`: Precios (€12/mes, €99/año)
- `FREE_LIMITS` y `FOUNDING_LIMITS`: Límites por plan

---

### 2. Store de Estado (Zustand)

**Archivo:** `frontend-nextjs/app/stores/usage-limit-store.ts`

Store global para manejar:
- `isOpen`: Estado del modal
- `limitInfo`: Información del límite alcanzado
- `showModal()`: Abrir modal con info
- `closeModal()`: Cerrar modal

---

### 3. Copy Deck (Internacionalización)

**Archivo:** `frontend-nextjs/copy/en.ts`

Se agregaron dos secciones nuevas:

#### `usageLimit`
- `modalTitle`: "You've reached today's free limit 💜"
- `voiceUsed`, `textUsed`, `reflectionsUsed`: Templates con {used}/{limit}
- `intro`, `ifYouFelt`, `benefits[]`, `noPressure`, `thankYou`: Copy empático
- `ctaPrimary`, `ctaSecondary`: Botones del modal
- `footerHint`: Hint en el footer

#### `foundingSupporter`
- `title`: "Why Founding Supporters Matter"
- `hero`: Todo el copy de Davide (10 párrafos + quote)
- `supporting`: 3 cards explicando qué se apoya
- `plans`: Comparación Free vs Founding Supporter
- `cta`, `ctaNotLive`: Botones de acción

---

### 4. Componente: UsageLimitModal

**Archivo:** `frontend-nextjs/app/components/UsageLimitModal.tsx`

**Características:**
- ✅ Modal centrado con backdrop oscuro
- ✅ Título y mensaje personalizado según `reason` (voice/text/reflections)
- ✅ Copy empático de Davide
- ✅ Lista de beneficios con bullets morados
- ✅ Dos botones: "I'll come back tomorrow" (secundario) y "Become a Founding Supporter" (primario)
- ✅ Focus trap y navegación por teclado
- ✅ ESC para cerrar
- ✅ Redirección a `/founding-supporter` o `NEXT_PUBLIC_FOUNDING_CHECKOUT_URL`
- ✅ Estilos cohesivos con el resto de la app (colores Sophia, rounded-3xl, shadow-soft)

---

### 5. Página: /founding-supporter

**Archivo:** `frontend-nextjs/app/founding-supporter/page.tsx`

**Secciones:**
1. **Hero**: Avatar de Sophia + título "Why Founding Supporters Matter"
2. **Hero Copy**: Todo el texto de Davide con párrafos, bullets y quote destacado
3. **What You're Supporting**: 3 cards (Emotional Brain, Human Connection, Long-Term Mission)
4. **Plans Comparison**: Grid de 2 columnas
   - **Free**: Lista de features con checks grises
   - **Founding Supporter**: Lista de features con checks morados, badge "Limited early phase"
5. **CTA**: Botón grande "Become a Founding Supporter"
6. **Toast**: Si no hay checkout URL, muestra "Payments are not live yet. Stay tuned 💜"

**Estilos:**
- ✅ Responsive (grid cambia a 1 columna en móvil)
- ✅ Colores Sophia (purple, bg, text, text2)
- ✅ Rounded corners (rounded-3xl)
- ✅ Shadows suaves (shadow-soft)
- ✅ Spacing generoso (space-y-16, space-y-6)
- ✅ Typography clara (text-3xl para títulos, text-sm para body)

---

### 6. Detección de Límites en SSE (Texto)

**Archivo:** `frontend-nextjs/app/lib/stream-conversation.ts`

**Cambios:**
- ✅ Agregado handler `onUsageLimit` a `StreamHandlers`
- ✅ Detección en eventos `error` del SSE: si `error === "USAGE_LIMIT_REACHED"`, llama `onUsageLimit`
- ✅ Detección en respuestas HTTP 429/403: verifica JSON y llama `onUsageLimit`
- ✅ Import de `UsageLimitError` type

**Archivo:** `frontend-nextjs/app/stores/chat-store.ts`

**Cambios:**
- ✅ Import de `useUsageLimitStore`
- ✅ Handler `onUsageLimit` en `sendMessage`:
  - Muestra modal con `useUsageLimitStore.showModal()`
  - Limpia mensaje de Sophia en progreso
  - Resetea estado de UI (isLocked, activeReplyId, feedbackGate)
  - Resetea presencia

---

### 7. Detección de Límites en WebSocket (Voz)

**Archivo:** `frontend-nextjs/app/hooks/useVoiceLoop.ts`

**Cambios:**
- ✅ Import de `useUsageLimitStore` y `UsageLimitError`
- ✅ En `handleServerMessage`, caso `error`:
  - Si `data.error === "USAGE_LIMIT_REACHED"`:
    - Construye `UsageLimitError` con todos los campos
    - Muestra modal con `useUsageLimitStore.showModal()`
    - Limpia playback queue
    - Resetea stage a "idle"
    - Resetea presencia
    - Emite telemetría `voice.usage_limit`
  - Si es otro error:
    - Comportamiento normal (setError, stage "error", etc.)

---

### 8. Integración Global del Modal

**Archivo:** `frontend-nextjs/app/components/AppShell.tsx`

**Cambios:**
- ✅ Import de `UsageLimitModal` y `useUsageLimitStore`
- ✅ Suscripción al store: `isOpen`, `limitInfo`, `closeModal`
- ✅ Render del modal al final del AppShell (siempre montado, controlado por `open`)

---

### 9. Indicador de Uso en Footer

**Archivo:** `frontend-nextjs/app/components/UsageHint.tsx`

Componente simple que muestra:
> "Free daily usage resets every 24 hours • Founding Supporters get higher limits"

**Archivo:** `frontend-nextjs/app/components/ConversationView.tsx`

**Cambios:**
- ✅ Import de `UsageHint`
- ✅ Agregado `<UsageHint />` debajo del composer
- ✅ Wrapped composer en un `div` con `space-y-2` para spacing

---

## 📁 Archivos Creados (8)

1. `frontend-nextjs/app/types/rate-limits.ts` - Tipos y constantes
2. `frontend-nextjs/app/stores/usage-limit-store.ts` - Store de Zustand
3. `frontend-nextjs/app/components/UsageLimitModal.tsx` - Modal de límite
4. `frontend-nextjs/app/founding-supporter/page.tsx` - Página de pricing
5. `frontend-nextjs/app/components/UsageHint.tsx` - Hint en footer
6. `RATE_LIMITS_IMPLEMENTATION.md` - Este documento

---

## 📝 Archivos Modificados (6)

1. **`frontend-nextjs/copy/en.ts`**
   - Agregado: `misc`, `usageLimit`, `foundingSupporter`

2. **`frontend-nextjs/app/lib/stream-conversation.ts`**
   - Agregado: `onUsageLimit` handler
   - Agregado: Detección de `USAGE_LIMIT_REACHED` en errores SSE y HTTP

3. **`frontend-nextjs/app/stores/chat-store.ts`**
   - Agregado: Import de `useUsageLimitStore`
   - Agregado: Handler `onUsageLimit` en `sendMessage`

4. **`frontend-nextjs/app/hooks/useVoiceLoop.ts`**
   - Agregado: Import de `useUsageLimitStore` y `UsageLimitError`
   - Agregado: Detección de `USAGE_LIMIT_REACHED` en mensajes WS

5. **`frontend-nextjs/app/components/AppShell.tsx`**
   - Agregado: Render de `UsageLimitModal`

6. **`frontend-nextjs/app/components/ConversationView.tsx`**
   - Agregado: `UsageHint` en el composer

---

## 🎨 Diseño y Estilos

### Paleta de Colores Usada
- `bg-sophia-purple` (#8b7ab8) - Botones primarios, badges, bullets
- `bg-sophia-glow` (#b896d4) - Hover de botones primarios
- `bg-sophia-bg` (#f8f7fa) - Fondo de la app
- `bg-sophia-reply` (#f0ebff) - Fondo de quote
- `text-sophia-text` (#2d2833) - Texto principal
- `text-sophia-text2` (#6b6672) - Texto secundario
- `border-sophia-text/10` - Bordes suaves

### Componentes Reutilizados
- `rounded-3xl` - Bordes redondeados grandes
- `rounded-2xl` - Bordes redondeados medianos
- `shadow-soft` - Sombra suave (0 8px 24px rgba(26, 7, 50, 0.08))
- `space-y-*` - Spacing vertical consistente
- `safe-px`, `safe-b` - Safe area insets para móviles

### Responsiveness
- Grid de 2 columnas → 1 columna en móvil (`md:grid-cols-2`)
- Flex row → column en móvil (`sm:flex-row`)
- Padding adaptativo (`px-4 md:px-8 lg:px-16`)
- Max-width contenedor (`max-w-4xl`)

---

## 🔌 Integración con Backend

### Contrato Esperado del Backend

#### Error de Límite (SSE o HTTP)
```json
{
  "error": "USAGE_LIMIT_REACHED",
  "reason": "voice" | "text" | "reflections",
  "plan_tier": "FREE" | "FOUNDING_SUPPORTER",
  "limit": 600,
  "used": 615,
  "message": "You've reached your free daily voice limit.",
  "body": "Sophia is still in her early days..."
}
```

#### Error de Límite (WebSocket)
```json
{
  "type": "error",
  "error": "USAGE_LIMIT_REACHED",
  "reason": "voice",
  "plan_tier": "FREE",
  "limit": 600,
  "used": 615,
  "message": "You've reached your free daily voice limit."
}
```

### Endpoints Necesarios del Backend

1. **Rate Limit Enforcement**
   - `/text-chat/stream` - Debe retornar error 429 o evento `error` con `USAGE_LIMIT_REACHED`
   - `/ws/voice` - Debe enviar mensaje de tipo `error` con `USAGE_LIMIT_REACHED`

2. **Stripe Checkout (Futuro)**
   - URL de checkout configurada en `NEXT_PUBLIC_FOUNDING_CHECKOUT_URL`
   - Por ahora, redirige a `/founding-supporter` si no está configurada

---

## 🧪 Testing

### Flujos a Probar

#### 1. Modal de Límite (Texto)
1. Simular que el backend retorna error 429 con `USAGE_LIMIT_REACHED`
2. Verificar que aparece el modal
3. Verificar que el mensaje muestra "X of Y free text messages today"
4. Click en "I'll come back tomorrow" → modal cierra
5. Click en "Become a Founding Supporter" → redirige a `/founding-supporter`

#### 2. Modal de Límite (Voz)
1. Simular que el WS envía mensaje de error con `USAGE_LIMIT_REACHED`
2. Verificar que aparece el modal
3. Verificar que el mensaje muestra "X of Y free voice minutes today"
4. Verificar que el audio se detiene
5. Verificar que el stage vuelve a "idle"

#### 3. Página /founding-supporter
1. Navegar a `http://localhost:3000/founding-supporter`
2. Verificar que todo el copy se muestra correctamente
3. Verificar responsive (desktop, tablet, móvil)
4. Click en "Become a Founding Supporter" → muestra toast "Payments are not live yet"
5. Configurar `NEXT_PUBLIC_FOUNDING_CHECKOUT_URL` → click redirige a esa URL

#### 4. Usage Hint
1. Ir a la conversación
2. Verificar que debajo del composer aparece el hint
3. Verificar que el texto es legible y no interfiere con el composer

---

## 📊 Métricas

- **Archivos creados:** 6
- **Archivos modificados:** 6
- **Líneas de código:** ~900
- **Componentes nuevos:** 3 (UsageLimitModal, FoundingSupporterPage, UsageHint)
- **Stores nuevos:** 1 (usage-limit-store)
- **Tipos nuevos:** 4 (UsageLimitReason, PlanTier, UsageLimitError, UsageLimitInfo)
- **Errores de linter:** 0
- **Tiempo de implementación:** ~2 horas

---

## 🚀 Estado del Feature

### Completado (100%)
- ✅ Tipos y constantes
- ✅ Store de estado
- ✅ Copy deck completo
- ✅ Modal de límite con A11y
- ✅ Página /founding-supporter
- ✅ Detección en SSE (texto)
- ✅ Detección en WebSocket (voz)
- ✅ Integración global
- ✅ Indicador de uso
- ✅ Sin errores de linter
- ✅ Estilos cohesivos

### Listo Para
- ✅ Testing en localhost
- ✅ Integración con backend (cuando implemente rate limits)
- ✅ Configuración de Stripe checkout URL
- ⏳ Deploy a staging (después de testing)

---

## 🔧 Configuración Necesaria

### Variables de Entorno

Agregar a `frontend-nextjs/.env.local`:

```bash
# Opcional: URL de Stripe checkout
NEXT_PUBLIC_FOUNDING_CHECKOUT_URL=https://checkout.stripe.com/...
```

Si no se configura, el botón redirige a `/founding-supporter` y muestra un toast.

---

## 💡 Decisiones de Diseño

### ¿Por qué un modal en lugar de inline?
- **Bloqueante pero suave**: El usuario no puede continuar sin tomar una decisión, pero el copy es empático.
- **Consistente**: Mismo modal para voz y texto.
- **Fácil de implementar**: Un solo componente global.

### ¿Por qué una página dedicada?
- **SEO**: `/founding-supporter` puede ser indexada y compartida.
- **Marketing**: Espacio para explicar la misión sin interrumpir la conversación.
- **Flexibilidad**: Puede ser enlazada desde Discord, emails, etc.

### ¿Por qué Zustand store?
- **Global**: El modal puede ser activado desde cualquier parte (SSE, WS, etc.).
- **Simple**: Solo 3 métodos (`showModal`, `closeModal`, estado).
- **Consistente**: Ya usamos Zustand para chat y presence.

### ¿Por qué no bloqueamos la UI completamente?
- **UX empática**: El usuario puede cerrar el modal y volver mañana.
- **No agresivo**: No es un hard paywall, es una invitación.
- **Confianza**: Respetamos la decisión del usuario.

---

## 📚 Documentos Relacionados

- `INTEGRATION_CHANGES.md` - Integración frontend-backend anterior
- `WHAT_TO_DO_NOW.md` - Guía de setup
- `QUICK_START.md` - Testing rápido
- `INTEGRATION_CHECKLIST.md` - Checklist exhaustivo

---

## 🎓 Aprendizajes

### Copy Matters
El copy de Davide es clave para que el paywall no se sienta agresivo. Cada palabra fue cuidadosamente elegida para transmitir:
- Honestidad ("She's not a finished product")
- Invitación ("If that resonates with you")
- Sin presión ("If money is tight... no pressure at all")
- Gratitud ("Either way, thank you")

### A11y desde el Inicio
- Focus trap en el modal
- ESC para cerrar
- Navegación por teclado
- ARIA labels
- Esto no fue "agregado después", fue parte del diseño desde el principio.

### Cohesión Visual
Usar los mismos colores, radios, sombras y spacing que el resto de la app hace que el feature se sienta nativo, no como un "add-on".

---

**Status:** ✅ **READY FOR TESTING**  
**Next Action:** Probar en localhost y coordinar con Jorge para implementar rate limits en el backend  
**Questions?** Revisar este documento o `INTEGRATION_CHANGES.md`

