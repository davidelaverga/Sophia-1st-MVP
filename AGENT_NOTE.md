# Agent Note - Sophia MVP Project Context

> **Última actualización**: 28 de Noviembre, 2025
> **Estado del proyecto**: Desarrollo activo - Frontend en progreso
> **Rama actual**: `ENHANCE-FE-LE`

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estado Actual del Proyecto](#estado-actual-del-proyecto)
3. [Trabajo Reciente en Frontend](#trabajo-reciente-en-frontend)
4. [Cómo Ejecutar el Proyecto](#cómo-ejecutar-el-proyecto)
5. [Arquitectura del Sistema](#arquitectura-del-sistema)
6. [Flujos Principales](#flujos-principales)
7. [Problemas Conocidos y Soluciones](#problemas-conocidos-y-soluciones)
8. [Configuración y Variables de Entorno](#configuración-y-variables-de-entorno)
9. [Estructura de Archivos Clave](#estructura-de-archivos-clave)
10. [Próximos Pasos](#próximos-pasos)

---

## 🎯 Resumen Ejecutivo

**Sophia** es un asistente de IA con inteligencia emocional diseñado para conectar con humanos a nivel emocional. El proyecto está en desarrollo activo, con trabajo reciente enfocado en:

- ✅ **Sistema de Rate Limits y Pagos**: Integración completa de límites de uso y planes de suscripción
- ✅ **Mejoras en UI/UX**: Efectos visuales, dark mode, mejoras en la experiencia de usuario
- ✅ **Corrección de Bugs de Voz**: Timeouts, limpieza de estado, prevención de estados colgados
- ✅ **Microphone Access**: Diagnósticos y manejo robusto de permisos
- ✅ **WebSocket Authentication**: Fix para autorización en conexiones de voz

**Rama actual**: `ENHANCE-FE-LE`  
**Último merge**: `feature/rate_payments` (commit `7d5ede4` - "fix ws voice")

---

## 📊 Estado Actual del Proyecto

### Trabajo Reciente Completado

#### 1. **Sistema de Rate Limits y Pagos** ✅
- **Archivos clave**:
  - `app/services/rate_limits.py` - Lógica de límites de uso
  - `app/services/plan_config.py` - Configuración de planes (FREE, SUPPORTER, FOUNDING_SUPPORTER)
  - `app/routers/usage_router.py` - Endpoints de uso
  - `app/routers/stripe_router.py` - Webhooks de Stripe
  - `frontend-nextjs/app/stores/usage-limit-store.ts` - Store de Zustand para límites
  - `frontend-nextjs/app/hooks/useUsageMonitor.ts` - Hook para monitorear uso

- **Funcionalidad**:
  - Límites diarios por plan (voz en segundos, mensajes de texto, reflexiones mensuales)
  - Alertas progresivas (hint 50-79%, toast 80-99%, modal 100%)
  - Actualización en tiempo real del uso después de cada interacción
  - Integración con Supabase para tracking de uso diario

#### 2. **Correcciones en Flujo de Voz** ✅ (RECIÉN COMPLETADO)
- **Problema**: El micrófono se quedaba en estado "thinking" indefinidamente (5+ minutos)
- **Solución implementada**:
  - Timeout de 60 segundos para estado "thinking"
  - Limpieza automática de estado al cambiar de modo (chat ↔ voz)
  - Prevención de auto-inicio del micrófono
  - Mejor detección de WebSockets colgados
  - `SessionFeedbackToast` solo se muestra en modo chat, no en voz

- **Archivos modificados**:
  - `frontend-nextjs/app/hooks/useVoiceLoop.ts` - Agregado timeout y `resetVoiceState()`
  - `frontend-nextjs/app/components/ConversationView.tsx` - Limpieza de estado al cambiar modo

#### 3. **WebSocket Authentication Fix** ✅
- **Problema**: Error "no tiene authorization" al conectar WebSocket de voz
- **Solución**: Agregado API key como query parameter en la URL del WebSocket
- **Archivo**: `frontend-nextjs/app/hooks/useVoiceLoop.ts` (líneas 449-452)

#### 4. **Microphone Access Improvements** ✅
- Diagnósticos completos de acceso al micrófono
- Mensaje elegante con colores de Sophia que aparece solo en modo voz
- Auto-dismiss después de 4 segundos
- **Archivos**:
  - `frontend-nextjs/app/lib/microphone-debug.ts`
  - `frontend-nextjs/app/lib/microphone-permissions.ts`
  - `frontend-nextjs/app/components/ConversationView.tsx`

#### 5. **Streaming de Tokens** ✅
- **Cambio**: Los tokens ya NO se muestran mientras llegan
- **Comportamiento**: Se acumulan en memoria y solo se muestra el mensaje completo cuando termina
- **Archivo**: `frontend-nextjs/app/stores/chat-store.ts` (líneas 222-228, 229-252)

#### 6. **Dark Mode Proposals** ✅
- Tres propuestas de dark mode implementadas:
  - Midnight Serenity
  - Twilight Calm
  - Deep Space
- Selector en Settings con preview en vivo
- **Archivos**:
  - `frontend-nextjs/app/components/SettingsSheet.tsx`
  - `frontend-nextjs/app/ThemeBootstrap.tsx`
  - `frontend-nextjs/app/globals.css`

---

## 🚀 Cómo Ejecutar el Proyecto

### Backend (FastAPI)

#### Prerrequisitos
- Python 3.11+
- `uv` (package manager) o `pip`
- Variables de entorno configuradas (ver sección de configuración)

#### Pasos para Ejecutar

```bash
# 1. Navegar al directorio del proyecto
cd Sophia-1st-MVP

# 2. Crear y activar entorno virtual (si usas uv)
uv venv
source .venv/bin/activate  # Linux/Mac
# O
.venv\Scripts\activate  # Windows

# 3. Instalar dependencias
uv sync
# O con pip:
pip install -r requirements.txt

# 4. Configurar variables de entorno
# Crear archivo .env en la raíz del proyecto
# Ver sección "Configuración y Variables de Entorno" abajo

# 5. Ejecutar el servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# O con uvicorn directamente:
uvicorn main:app --reload
```

#### Verificar que Funciona
- Abrir navegador en: `http://localhost:8000/docs`
- Deberías ver la documentación interactiva de FastAPI (Swagger UI)
- Endpoint de health: `http://localhost:8000/health`

#### Estructura del Backend
```
Sophia-1st-MVP/
├── main.py                 # Punto de entrada, configuración FastAPI
├── app/
│   ├── config.py          # Configuración y settings
│   ├── deps.py            # Dependencias (auth, rate limiting)
│   ├── routers/           # Endpoints de la API
│   │   ├── text_chat.py  # Chat de texto (streaming)
│   │   ├── usage_router.py # Límites de uso
│   │   ├── stripe_router.py # Webhooks de Stripe
│   │   └── reflections.py # Reflexiones
│   └── services/          # Lógica de negocio
│       ├── rate_limits.py # Sistema de límites
│       ├── plan_config.py # Configuración de planes
│       ├── mistral.py     # Integración con Mistral AI
│       ├── tts.py         # Text-to-speech (Inworld)
│       └── supabase.py    # Cliente de Supabase
└── requirements.txt        # Dependencias Python
```

---

### Frontend (Next.js 14)

#### Prerrequisitos
- Node.js 18+ (recomendado 20+)
- npm o yarn

#### Pasos para Ejecutar

```bash
# 1. Navegar al directorio del frontend
cd frontend-nextjs

# 2. Instalar dependencias
npm install

# 3. Configurar variables de entorno
# Crear archivo .env.local en frontend-nextjs/
# Ver sección "Configuración y Variables de Entorno" abajo

# 4. Ejecutar servidor de desarrollo
npm run dev

# O con yarn:
yarn dev
```

#### Verificar que Funciona
- Abrir navegador en: `http://localhost:3000`
- Deberías ver la interfaz de Sophia
- El frontend se conecta automáticamente al backend en `http://localhost:8000`

#### Estructura del Frontend
```
frontend-nextjs/
├── app/
│   ├── page.tsx                    # Página principal
│   ├── layout.tsx                  # Layout raíz
│   ├── components/                 # Componentes React
│   │   ├── ConversationView.tsx   # Vista principal de conversación
│   │   ├── VoicePanel.tsx          # Panel de voz (modo full)
│   │   ├── VoiceFocusView.tsx      # Vista de voz (modo focus)
│   │   ├── Waveform.tsx            # Visualización de audio
│   │   ├── SettingsSheet.tsx        # Configuración y dark mode
│   │   └── SessionFeedbackToast.tsx # Toast de feedback
│   ├── hooks/                      # Custom hooks
│   │   ├── useVoiceLoop.ts         # Hook principal de voz (WebSocket)
│   │   ├── useUsageMonitor.ts      # Monitoreo de uso
│   │   └── useReflectionPrompt.ts  # Prompts de reflexión
│   ├── stores/                     # Zustand stores
│   │   ├── chat-store.ts           # Estado del chat
│   │   ├── presence-store.ts       # Estado de presencia de Sophia
│   │   ├── usage-limit-store.ts    # Estado de límites de uso
│   │   └── focus-mode-store.ts     # Estado de modo (full/text/voice)
│   ├── lib/                        # Utilidades
│   │   ├── stream-conversation.ts  # Streaming de conversación
│   │   ├── microphone-debug.ts     # Diagnósticos de micrófono
│   │   ├── microphone-permissions.ts # Permisos de micrófono
│   │   └── usage-tracker.ts        # Lógica de alertas de uso
│   ├── api/                        # API routes de Next.js (proxies)
│   │   └── conversation/
│   │       └── respond/route.ts    # Proxy para chat de texto
│   └── providers.tsx               # Providers de React
├── package.json                    # Dependencias
└── .env.local                      # Variables de entorno (NO commitear)
```

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

#### Backend
- **FastAPI** (Python) - Framework web
- **Mistral Voxtral** - Speech-to-text y LLM
- **Google Gemini** - Fallback para transcripción
- **Inworld AI** - Text-to-speech con emociones
- **Supabase** - Base de datos PostgreSQL + Auth
- **LangGraph** - Orquestación de conversaciones
- **OpenTelemetry** - Observabilidad (trazas a Grafana Cloud)
- **WebSocket** - Comunicación en tiempo real para voz

#### Frontend
- **Next.js 14** - Framework React con App Router
- **TypeScript** - Tipado estático
- **Tailwind CSS** - Estilos utility-first
- **Zustand** - State management (stores)
- **WebRTC/MediaRecorder** - Captura de audio
- **WebSocket API** - Conexión directa al backend para voz
- **Supabase Auth** - Autenticación de usuarios

### Flujo de Datos

```
Usuario (Frontend)
    ↓
Next.js API Routes (/api/*) → Backend FastAPI
    ↓
Supabase (Auth + Database)
    ↓
Servicios de IA (Mistral/Gemini/Inworld)
    ↓
Respuesta → Frontend (Streaming)
```

### Comunicación en Tiempo Real

#### Chat de Texto
```
Frontend → /api/conversation/respond (Next.js API route)
    → Proxies a → Backend /text-chat/stream
    → Server-Sent Events (SSE) → Frontend
    → Tokens se acumulan → Mensaje completo al final
```

#### Voz
```
Frontend → WebSocket directo a ws://backend/ws/voice?api_key=...&user_id=...
    → Envía audio PCM16 en tiempo real
    → Recibe tokens, audio chunks, eventos
    → Reproduce audio cuando llega
```

---

## 🔄 Flujos Principales

### 1. Flujo de Chat de Texto

```
1. Usuario escribe mensaje en Composer
2. ConversationView → chat-store.sendMessage()
3. chat-store crea mensaje de usuario y mensaje vacío de Sophia
4. Llama a streamConversation() con handlers:
   - onToken: Acumula tokens (NO muestra en UI)
   - onDone: Muestra mensaje completo
   - onMeta: Actualiza presencia, límites de uso
5. Backend procesa con LangGraph/Mistral
6. Respuesta completa se muestra
7. SessionFeedbackToast aparece (solo en modo chat)
8. refreshUsage() actualiza límites
```

**Archivos clave**:
- `frontend-nextjs/app/stores/chat-store.ts` - Lógica de envío
- `frontend-nextjs/app/lib/stream-conversation.ts` - Streaming
- `frontend-nextjs/app/api/conversation/respond/route.ts` - Proxy
- `app/routers/text_chat.py` - Endpoint backend

---

### 2. Flujo de Voz

```
1. Usuario hace click en botón de micrófono
2. VoiceFocusView/VoicePanel → voiceState.startTalking()
3. useVoiceLoop.startTalking():
   a. Verifica permisos de micrófono
   b. Conecta WebSocket (ensureConnection)
   c. Obtiene stream de micrófono (getUserMedia)
   d. Procesa audio a PCM16
   e. Envía chunks al WebSocket
4. Usuario deja de hablar (click de nuevo)
5. stopTalking() → envía señal de fin
6. Backend procesa y responde:
   - Envía tokens (acumulados, no mostrados)
   - Envía audio chunks
   - Envía "reply_done"
7. Frontend reproduce audio
8. refreshUsage() actualiza límites
```

**Estados del micrófono**:
- `idle` - Listo para grabar
- `connecting` - Conectando WebSocket
- `listening` - Grabando audio
- `thinking` - Procesando (con timeout de 60s)
- `speaking` - Reproduciendo respuesta
- `error` - Error ocurrido

**Archivos clave**:
- `frontend-nextjs/app/hooks/useVoiceLoop.ts` - Lógica completa de voz
- `frontend-nextjs/app/components/VoiceFocusView.tsx` - UI de voz
- `main.py` (línea 709) - Endpoint WebSocket `/ws/voice`

---

### 3. Flujo de Rate Limits

```
1. Usuario envía mensaje (texto o voz)
2. Backend recibe user_id
3. rate_limits.py verifica límites:
   - Consulta user_daily_usage en Supabase
   - Compara con límites del plan
   - Si < 100%: Permite y actualiza uso
   - Si = 100%: Rechaza con USAGE_LIMIT_REACHED
4. Backend envía meta events con usage_info:
   - 50-79%: hint (sutil)
   - 80-99%: toast (gentle)
   - 100%: modal (bloquea)
5. Frontend muestra alerta correspondiente
6. refreshUsage() actualiza display
```

**Archivos clave**:
- `app/services/rate_limits.py` - Lógica de límites
- `app/services/plan_config.py` - Configuración de planes
- `frontend-nextjs/app/stores/usage-limit-store.ts` - Store de límites
- `frontend-nextjs/app/hooks/useUsageMonitor.ts` - Monitoreo

---

### 4. Flujo de Cambio de Modo (Focus Modes)

```
Modos disponibles:
- "full" - Vista completa (chat + voz)
- "text" - Solo chat (composer visible)
- "voice" - Solo voz (micrófono visible)

Cambio automático:
1. Usuario usa voz → auto-switch a "voice"
2. Usuario escribe → auto-switch a "text"
3. Usuario sale de ambos → vuelve a "full" (solo si no hay override manual)

Cambio manual:
- Click en "Switch to voice mode" → setMode("voice")
- Click en "Switch to chat mode" → setMode("text")

Limpieza de estado:
- Al salir de modo voz → resetVoiceState() limpia WebSocket y estado
- Previene estados colgados cuando cambias de modo
```

**Archivos clave**:
- `frontend-nextjs/app/stores/focus-mode-store.ts` - Estado de modo
- `frontend-nextjs/app/components/ConversationView.tsx` - Lógica de auto-switch
- `frontend-nextjs/app/hooks/useVoiceLoop.ts` - resetVoiceState()

---

## ⚠️ Problemas Conocidos y Soluciones

### 1. ✅ RESUELTO: Micrófono se queda en "thinking" indefinidamente

**Problema**: Después de usar chat y cambiar a voz, el micrófono se quedaba pensando por 5+ minutos.

**Causa**: 
- No había timeout para estado "thinking"
- Estado persistía al cambiar de modo
- WebSocket podía quedar colgado

**Solución implementada**:
- Timeout de 60 segundos para "thinking"
- `resetVoiceState()` limpia todo al cambiar de modo
- Mejor detección de WebSockets en estados inválidos
- Limpieza de timeouts en todos los handlers

**Archivos modificados**:
- `frontend-nextjs/app/hooks/useVoiceLoop.ts`
- `frontend-nextjs/app/components/ConversationView.tsx`

---

### 2. ✅ RESUELTO: Error "no tiene authorization" en WebSocket

**Problema**: Algunos usuarios recibían error de autorización al conectar WebSocket.

**Causa**: El WebSocket no enviaba el API key al backend.

**Solución**: Agregado API key como query parameter:
```typescript
wsUrl += `?api_key=${encodeURIComponent(apiKey)}&user_id=${userId}`
```

**Archivo**: `frontend-nextjs/app/hooks/useVoiceLoop.ts` (líneas 449-457)

---

### 3. ✅ RESUELTO: SessionFeedbackToast bloqueaba el micrófono

**Problema**: El toast de feedback aparecía en modo voz y bloqueaba la interacción.

**Solución**: Solo se muestra en modo chat:
```tsx
{!chunks && focusMode !== "voice" && <SessionFeedbackToast />}
```

**Archivo**: `frontend-nextjs/app/components/ConversationView.tsx` (línea 216)

---

### 4. ⚠️ CONOCIDO: Error "Failed to export batch code: 401" en logs

**Problema**: Aparece cada ~5 segundos en logs del backend.

**Causa**: OpenTelemetry intenta exportar trazas a Grafana Cloud pero las credenciales no están configuradas o son inválidas.

**Impacto**: No afecta funcionalidad, solo ruido en logs.

**Solución temporal**: 
- Configurar `OTEL_EXPORTER_OTLP_ENDPOINT` y `OTEL_EXPORTER_OTLP_HEADERS` correctamente
- O deshabilitar OpenTelemetry si no se usa

**Archivo**: `main.py` (líneas 75-90)

---

### 5. ⚠️ CONOCIDO: Archivos .next/ causan conflictos en git

**Problema**: Los archivos de build de Next.js aparecen en git y causan conflictos en merge.

**Solución**: 
- Ya están en `.gitignore` pero pueden estar siendo rastreados
- Ejecutar: `git rm -r --cached frontend-nextjs/.next/`
- Luego: `git commit -m "Remove .next/ from tracking"`

---

## 🔧 Configuración y Variables de Entorno

### Backend (.env en raíz del proyecto)

```bash
# API Configuration
API_KEYS=dev-key,staging-key-1,staging-key-2
API_RATE_LIMIT=30/minute

# Mistral AI
MISTRAL_API_KEY=your_mistral_key
MISTRAL_API_BASE=https://api.mistral.ai

# Google Gemini (fallback)
GOOGLE_API_KEY=your_google_key

# Inworld AI (TTS)
INWORLD_API_KEY=your_inworld_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
SUPABASE_DB_DSN=postgresql://user:pass@host:port/db
SUPABASE_BUCKET_AUDIO=Audio Storage
SUPABASE_AUDIO_PREFIX=uploads/

# OpenTelemetry (opcional)
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic your_token

# Redis (opcional, para caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Frontend (.env.local en frontend-nextjs/)

```bash
# Backend API (server-side only, NO expuesto al browser)
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-key

# Public API (expuesto al browser)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000
NEXT_PUBLIC_API_KEY=dev-key

# Supabase (autenticación)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# NextAuth (opcional)
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_secret_here

# Mock Privacy APIs (solo desarrollo)
NEXT_PUBLIC_MOCK_PRIVACY=false
```

### Producción

**Backend (Render/Fly.io)**:
- Configurar todas las variables de `.env` como secrets
- `API_KEYS` debe incluir las keys de producción
- `OTEL_EXPORTER_OTLP_*` para observabilidad

**Frontend (Vercel)**:
- Configurar en Vercel Dashboard → Settings → Environment Variables
- `BACKEND_API_URL` → URL de producción del backend
- `NEXT_PUBLIC_BACKEND_WS_URL` → WebSocket URL (wss://)
- Todas las `NEXT_PUBLIC_*` variables

---

## 📁 Estructura de Archivos Clave

### Frontend - Componentes Principales

#### `app/components/ConversationView.tsx`
- **Rol**: Componente principal que orquesta toda la UI
- **Responsabilidades**:
  - Maneja cambio entre modos (full/text/voice)
  - Auto-switch basado en interacción del usuario
  - Muestra mensajes de chat
  - Integra VoicePanel, VoiceFocusView, Composer
  - Maneja micrófono support warning
- **Estado clave**: `focusMode`, `voiceStage`, `isLocked`

#### `app/hooks/useVoiceLoop.ts`
- **Rol**: Hook principal para toda la funcionalidad de voz
- **Responsabilidades**:
  - Maneja WebSocket connection
  - Captura audio del micrófono
  - Procesa audio a PCM16
  - Reproduce audio de respuesta
  - Maneja estados (idle, listening, thinking, speaking)
  - Timeouts y recuperación de errores
- **Estado expuesto**: `stage`, `partialReply`, `finalReply`, `error`, `stream`
- **Funciones expuestas**: `startTalking()`, `stopTalking()`, `bargeIn()`, `resetVoiceState()`

#### `app/stores/chat-store.ts`
- **Rol**: Estado global del chat (Zustand)
- **Responsabilidades**:
  - Mensajes (array de ChatMessage)
  - Envío de mensajes (streaming)
  - Manejo de feedback
  - Integración con presence store
- **Cambio reciente**: Tokens se acumulan, no se muestran hasta `onDone`

#### `app/stores/usage-limit-store.ts`
- **Rol**: Estado de límites de uso
- **Responsabilidades**:
  - Almacena uso actual (voicePercent, textPercent)
  - Muestra hints, toasts, modals según porcentaje
  - Bloquea interacción si está en 100%

#### `app/stores/focus-mode-store.ts`
- **Rol**: Estado del modo de focus
- **Valores**: `"full"` | `"text"` | `"voice"`
- **Funciones**: `setMode()`, `setManualOverride()`

### Backend - Archivos Principales

#### `main.py`
- **Rol**: Punto de entrada de FastAPI
- **Configuración**:
  - OpenTelemetry setup
  - CORS middleware
  - Rate limiting
  - WebSocket endpoint `/ws/voice`
- **Endpoints principales**:
  - `/text-chat/stream` - Chat de texto (SSE)
  - `/ws/voice` - WebSocket de voz
  - `/health` - Health check

#### `app/services/rate_limits.py`
- **Rol**: Lógica de rate limiting
- **Funciones clave**:
  - `check_usage_limits()` - Verifica si usuario puede usar el servicio
  - `add_text_usage()` - Actualiza uso de texto
  - `add_voice_usage()` - Actualiza uso de voz
  - Fallback a INSERT/UPDATE directo si RPC falla

#### `app/routers/text_chat.py`
- **Rol**: Endpoint de chat de texto
- **Flujo**:
  1. Recibe mensaje + user_id
  2. Verifica límites
  3. Procesa con LangGraph/Mistral
  4. Streams respuesta (SSE)
  5. Actualiza uso al finalizar

---

## 🔍 Debugging y Troubleshooting

### Problemas Comunes

#### 1. "Voice service unavailable"
**Causa**: WebSocket no puede conectar al backend
**Solución**:
- Verificar que backend esté corriendo en `NEXT_PUBLIC_BACKEND_WS_URL`
- Verificar que API key sea correcta
- Revisar CORS en backend
- Verificar que URL use `ws://` (dev) o `wss://` (prod)

#### 2. "Microphone access is blocked"
**Causa**: Permisos denegados en navegador
**Solución**:
- Verificar que esté en HTTPS o localhost
- Ir a configuración del navegador → Permisos → Micrófono
- Resetear permisos del sitio

#### 3. "Usage limits not updating"
**Causa**: user_id no se está pasando correctamente
**Solución**:
- Verificar que `useUsageMonitor` esté guardando `user.id`
- Verificar que `chat-store` pase `user_id` en request
- Revisar logs del backend para ver si recibe `user_id`

#### 4. Estado "thinking" se queda colgado
**Causa**: Backend no responde o WebSocket se desconecta
**Solución** (ya implementada):
- Timeout de 60s resetea automáticamente
- `resetVoiceState()` limpia estado
- Verificar logs del backend para ver qué está pasando

### Comandos Útiles para Debugging

```bash
# Ver logs del backend en tiempo real
# (si está corriendo con uvicorn --reload, los logs aparecen en consola)

# Ver estado de git
git status
git log --oneline -10

# Verificar variables de entorno (frontend)
cd frontend-nextjs
cat .env.local

# Verificar variables de entorno (backend)
cat .env

# Verificar que puertos estén libres
# Windows:
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# Linux/Mac:
lsof -i :8000
lsof -i :3000
```

---

## 🎨 Sistema de Diseño y Temas

### Colores de Sophia (CSS Variables)

Definidos en `frontend-nextjs/app/globals.css`:

**Light Mode (default)**:
- `--sophia-purple`: Color principal
- `--sophia-glow`: Color de glow/brillo
- `--sophia-text`: Texto principal
- `--sophia-text2`: Texto secundario
- `--sophia-user`: Burbuja de usuario
- `--sophia-reply`: Burbuja de Sophia
- `--sophia-bubble`: Fondo de burbujas
- `--sophia-error`: Errores

**Dark Modes** (3 propuestas):
- `data-sophia-theme="midnight"` - Midnight Serenity
- `data-sophia-theme="twilight"` - Twilight Calm
- `data-sophia-theme="deep-space"` - Deep Space

### Componentes de UI Clave

- **Waveform**: Visualización de audio con estados (resting, listening, thinking, speaking)
- **MessageBubble**: Burbujas de mensajes (usuario a la derecha, Sophia a la izquierda)
- **VoicePanel**: Panel completo de voz (modo full)
- **VoiceFocusView**: Vista minimalista de voz (modo focus)
- **SettingsSheet**: Modal de configuración con selector de tema

---

## 📝 Próximos Pasos

### Tareas Pendientes Identificadas

1. **Resolver error de OpenTelemetry** (opcional)
   - Configurar credenciales correctas o deshabilitar
   - Archivo: `main.py` líneas 75-90

2. **Mejorar manejo de errores de WebSocket**
   - Agregar más logging para debugging
   - Mejorar mensajes de error al usuario

3. **Optimizar polling de usage**
   - Actualmente se hace cada 5 segundos
   - Podría optimizarse con WebSockets o Server-Sent Events

4. **Testing**
   - Agregar tests para flujo de voz
   - Tests para rate limits
   - Tests para cambio de modos

### Mejoras Sugeridas

1. **Persistencia de tema**
   - Ya implementado con localStorage
   - Verificar que funcione correctamente

2. **Mejor feedback visual**
   - Indicadores más claros de estado
   - Mejor manejo de errores visuales

3. **Performance**
   - Optimizar re-renders innecesarios
   - Lazy loading de componentes pesados

---

## 🔗 Enlaces Útiles

### Documentación
- **FastAPI**: https://fastapi.tiangolo.com/
- **Next.js 14**: https://nextjs.org/docs
- **Zustand**: https://zustand-demo.pmnd.rs/
- **WebSocket API**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

### Repositorio
- **GitHub**: https://github.com/davidelaverga/Sophia-1st-MVP
- **Rama actual**: `ENHANCE-FE-LE`
- **Rama de rate_payments**: `feature/rate_payments`

### Endpoints Importantes

**Backend**:
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/text-chat/stream` - Chat de texto
- `ws://localhost:8000/ws/voice` - WebSocket de voz

**Frontend**:
- `http://localhost:3000` - App principal
- `http://localhost:3000/api/conversation/respond` - Proxy de chat
- `http://localhost:3000/api/usage/limits` - Límites de uso

---

## 💡 Notas Importantes para Nuevos Agentes

### ⚠️ Cosas que NO Hacer

1. **NO mostrar tokens mientras llegan** - Ya está implementado, los tokens se acumulan y solo se muestran al final
2. **NO auto-iniciar el micrófono** - El micrófono solo se activa cuando el usuario hace click explícitamente
3. **NO olvidar pasar user_id** - Es crítico para rate limiting, siempre verificar que se pase
4. **NO commitear archivos .next/** - Son archivos de build, no deben estar en git
5. **NO hardcodear API keys** - Siempre usar variables de entorno

### ✅ Buenas Prácticas

1. **Siempre verificar estado antes de operaciones**
   - Verificar `isLocked` antes de enviar mensaje
   - Verificar `isAtLimit` antes de permitir interacción
   - Verificar `focusMode` antes de mostrar componentes

2. **Usar stores de Zustand correctamente**
   - No mutar estado directamente
   - Usar las funciones del store
   - Verificar que el store esté inicializado

3. **Manejar errores gracefully**
   - Mostrar mensajes amigables al usuario
   - Loggear detalles técnicos en consola
   - No bloquear la UI con errores

4. **Limpiar recursos**
   - Cerrar WebSockets en cleanup
   - Limpiar timeouts en useEffect cleanup
   - Detener streams de audio cuando no se usan

### 🎯 Prioridades Actuales

1. **Estabilidad del flujo de voz** - Asegurar que no se quede colgado
2. **Rate limits funcionando** - Verificar que se actualicen correctamente
3. **UX suave** - Transiciones y feedback visual
4. **Performance** - Optimizar re-renders y carga

---

## 📞 Contacto y Soporte

Si tienes preguntas sobre el proyecto:

1. **Revisar este documento primero** - La mayoría de la información está aquí
2. **Revisar logs** - Backend y frontend tienen logging detallado
3. **Revisar código** - Los comentarios en el código explican la lógica
4. **Git history** - Ver commits recientes para entender cambios

---

## 🔄 Última Actualización

**Fecha**: 28 de Noviembre, 2025  
**Cambios recientes**:
- ✅ Timeout para estado "thinking" (60s)
- ✅ Limpieza de estado al cambiar de modo
- ✅ SessionFeedbackToast solo en modo chat
- ✅ Mejoras en detección de WebSocket colgado
- ✅ Microphone access note mejorado (estético, auto-dismiss)

**Próxima sesión**: Continuar mejoras en estabilidad y UX

---

**Este documento se actualiza con cada cambio significativo. Mantenerlo actualizado es responsabilidad del equipo.**



