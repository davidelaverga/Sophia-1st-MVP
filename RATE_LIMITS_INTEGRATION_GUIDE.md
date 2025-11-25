# 💜 Guía de Integración: Rate Limits Gentiles para Sophia

## 📋 Resumen

Hemos integrado un sistema de **rate limiting gentil y amable** en Sophia que:
- ✅ **No rompe nada existente** - Es completamente opcional
- ✅ **Responde con mensajes cálidos** cuando se alcanza el límite
- ✅ **Trackea uso automáticamente** después de cada interacción
- ✅ **Funciona con voz y texto** en todos los endpoints

---

## 🎯 ¿Cómo Funciona?

### 1. **Verificación ANTES de procesar**
Si el frontend envía un `user_id`, el backend verifica si el usuario tiene límites disponibles.

### 2. **Respuesta gentil si se alcanza el límite**
En lugar de un error frío, Sophia responde con un mensaje cálido explicando:
- Por qué existe el límite
- Cómo pueden continuar (Founding Supporter)
- Que pueden volver mañana sin presión 💜

### 3. **Tracking DESPUÉS de procesar**
Una vez que la interacción es exitosa, se registra el uso (segundos de voz o mensajes de texto).

---

## 🔧 Endpoints Modificados

### 1. `/text-chat` (Chat de Texto)

**Nuevo parámetro opcional:**
```json
{
  "message": "Hola Sophia",
  "session_id": "optional-uuid",
  "user_id": "uuid-del-usuario-de-supabase"  // ← NUEVO (opcional)
}
```

**Respuesta cuando se alcanza el límite (HTTP 429):**
```json
{
  "detail": {
    "error": "USAGE_LIMIT_REACHED",
    "reason": "text",
    "plan_tier": "FREE",
    "limit": 40,
    "used": 40,
    "title": "You've reached today's free text limit 💜",
    "body": "Sophia is still in her early days..."
  }
}
```

---

### 2. `/defi-chat` (Chat de Voz)

**Nuevo parámetro opcional:**
```
POST /defi-chat
Content-Type: multipart/form-data

file: <audio-file>
session_id: optional-uuid
user_id: uuid-del-usuario-de-supabase  // ← NUEVO (opcional)
```

**Respuesta cuando se alcanza el límite (HTTP 429):**
```json
{
  "detail": {
    "error": "USAGE_LIMIT_REACHED",
    "reason": "voice",
    "plan_tier": "FREE",
    "limit": 600,
    "used": 605,
    "title": "You've reached today's free voice limit 💜",
    "body": "Sophia is still in her early days..."
  }
}
```

---

### 3. `/ws/voice` (WebSocket de Voz en Vivo)

**Nuevo query parameter opcional:**
```javascript
const ws = new WebSocket(
  `wss://api.sophia.com/ws/voice?user_id=uuid-del-usuario`
);
```

**Mensaje cuando se alcanza el límite:**
```json
{
  "type": "error",
  "error": "USAGE_LIMIT_REACHED",
  "reason": "voice",
  "plan_tier": "FREE",
  "limit": 600,
  "used": 610,
  "title": "You've reached today's free voice limit 💜",
  "body": "Sophia is still in her early days..."
}
```

**Nota:** El WebSocket NO se cierra, solo se detiene el procesamiento de ese turno. El usuario puede seguir conectado.

---

## 📊 Planes y Límites

### Plan FREE (Gratis)
- 🎤 **10 minutos de voz por día** (600 segundos)
- 💬 **40 mensajes de texto por día**
- 📝 **4 Reflection Cards por mes**

### Plan SUPPORTER
- 🎤 **60 minutos de voz por día** (3600 segundos)
- 💬 **200 mensajes de texto por día**
- 📝 **30 Reflection Cards por mes**

### Plan FOUNDING_SUPPORTER
- 🎤 **120 minutos de voz por día** (7200 segundos)
- 💬 **400 mensajes de texto por día**
- 📝 **100 Reflection Cards por mes**

---

## 🎨 Integración en el Frontend

### Paso 1: Obtener el user_id

El `user_id` es el UUID del usuario autenticado en Supabase:

```typescript
// En Next.js con Supabase
const { data: { user } } = await supabase.auth.getUser();
const userId = user?.id;
```

### Paso 2: Enviar user_id en las peticiones

#### Para Chat de Texto:
```typescript
const response = await fetch('/api/conversation/respond', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage,
    user_id: userId,  // ← Agregar aquí
  }),
});

// Verificar si se alcanzó el límite
if (response.status === 429) {
  const error = await response.json();
  if (error.detail?.error === 'USAGE_LIMIT_REACHED') {
    // Mostrar modal gentil con error.detail.title y error.detail.body
    showUsageLimitModal(error.detail);
  }
}
```

#### Para Chat de Voz:
```typescript
const formData = new FormData();
formData.append('file', audioBlob, 'audio.wav');
formData.append('user_id', userId);  // ← Agregar aquí

const response = await fetch('/api/conversation/respond', {
  method: 'POST',
  body: formData,
});

// Mismo manejo de error 429
```

#### Para WebSocket de Voz:
```typescript
const ws = new WebSocket(
  `${wsUrl}/ws/voice?user_id=${userId}`  // ← Agregar como query param
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'error' && data.error === 'USAGE_LIMIT_REACHED') {
    // Mostrar modal gentil
    showUsageLimitModal(data);
  }
};
```

---

## 🎭 Componente Modal Sugerido

```typescript
interface UsageLimitModalProps {
  open: boolean;
  onClose: () => void;
  limitInfo: {
    reason: 'voice' | 'text' | 'reflections';
    plan_tier: string;
    limit: number;
    used: number;
    title: string;
    body: string;
  };
}

export function UsageLimitModal({ open, onClose, limitInfo }: UsageLimitModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-neutral-950/95 border border-neutral-800 p-6 flex flex-col gap-4">
        <h2 className="text-xl font-semibold">{limitInfo.title}</h2>
        
        <p className="text-sm text-neutral-400">
          {limitInfo.reason === 'voice' && 
            `You've used ${Math.round(limitInfo.used / 60)} of ${Math.round(limitInfo.limit / 60)} free voice minutes today.`
          }
          {limitInfo.reason === 'text' && 
            `You've used ${limitInfo.used} of ${limitInfo.limit} free text messages today.`
          }
        </p>
        
        <div className="text-sm text-neutral-200 whitespace-pre-line">
          {limitInfo.body}
        </div>
        
        <div className="flex flex-col gap-2 mt-2 sm:flex-row sm:justify-end">
          <button
            onClick={onClose}
            className="w-full sm:w-auto rounded-lg border border-neutral-700 px-4 py-2 text-sm"
          >
            I'll come back tomorrow
          </button>
          <button
            onClick={() => window.location.href = '/founding-supporter'}
            className="w-full sm:w-auto rounded-lg bg-purple-500 hover:bg-purple-400 px-4 py-2 text-sm font-medium"
          >
            Become a Founding Supporter
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## 🗄️ Configuración de Base de Datos

### Ejecutar Migración SQL

El archivo `app/migrations/rate_limits.sql` contiene las tablas necesarias:

1. **`user_daily_usage`** - Trackea uso diario de voz y texto
2. **`reflection_cards`** - Trackea Reflection Cards mensuales
3. **Función `upsert_user_daily_usage`** - Para actualizar uso atómicamente

**Para aplicar:**
```bash
# En Supabase Dashboard > SQL Editor
# Copiar y ejecutar el contenido de: app/migrations/rate_limits.sql
```

---

## 🔍 Endpoints de Consulta

### Ver uso actual del usuario
```
GET /api/usage/limits?user_id=uuid-del-usuario
```

**Respuesta:**
```json
{
  "user_id": "uuid",
  "plan_tier": "FREE",
  "daily_voice": {
    "used": 245,
    "limit": 600,
    "remaining": 355
  },
  "daily_text": {
    "used": 12,
    "limit": 40,
    "remaining": 28
  },
  "monthly_reflections": {
    "used": 2,
    "limit": 4,
    "remaining": 2
  }
}
```

### Ver todos los planes disponibles
```
GET /api/usage/plans
```

---

## 🚀 Despliegue

### Variables de Entorno Necesarias

Ya están configuradas (no se necesitan nuevas):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Archivos Nuevos Agregados

```
app/
├── services/
│   ├── rate_limits.py          ← Servicio principal
│   └── plan_config.py          ← Configuración de planes
├── routers/
│   ├── usage_router.py         ← API de consulta de uso
│   └── stripe_router.py        ← API de pagos (placeholder)
└── migrations/
    └── rate_limits.sql         ← SQL para crear tablas
```

### Archivos Modificados

```
main.py                         ← Integración en endpoints
```

---

## ✅ Testing

### Probar sin user_id (comportamiento actual)
```bash
# Todo funciona igual que antes
curl -X POST http://localhost:8000/text-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Probar con user_id
```bash
# Con límites activados
curl -X POST http://localhost:8000/text-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test-user-uuid"}'
```

### Simular límite alcanzado

1. Crear usuario de prueba en Supabase con `plan_tier = 'FREE'`
2. Insertar uso alto en `user_daily_usage`:
```sql
INSERT INTO user_daily_usage (user_id, usage_date, text_messages)
VALUES ('test-user-uuid', CURRENT_DATE, 40);
```
3. Hacer petición con ese `user_id` → Debería retornar 429

---

## 🎯 Próximos Pasos

1. **Frontend:** Agregar `user_id` a todas las peticiones
2. **Frontend:** Crear componente `UsageLimitModal`
3. **Frontend:** Manejar errores 429 con el modal
4. **Backend:** Ejecutar SQL migration en Supabase
5. **Testing:** Probar flujo completo con usuarios reales
6. **Stripe:** Integrar pagos cuando estén listos

---

## 💡 Notas Importantes

### ¿Por qué es opcional?
- **No rompe nada existente** - Si no se envía `user_id`, todo funciona como antes
- **Gradual rollout** - Puedes activarlo solo para usuarios autenticados
- **Desarrollo local** - No necesitas configurar nada para desarrollar

### ¿Qué pasa si falla el tracking?
- Se registra un warning en los logs
- **La petición sigue siendo exitosa** - No queremos bloquear a Sophia por un error de tracking

### ¿Los límites se resetean automáticamente?
- **Sí** - Los límites diarios se resetean a las 00:00 UTC
- Los límites mensuales se resetean el día 1 de cada mes

---

## 🆘 Troubleshooting

### "No se está trackeando el uso"
1. Verificar que `user_id` se está enviando
2. Verificar logs del backend: `"Tracked X usage for user Y"`
3. Verificar tabla `user_daily_usage` en Supabase

### "Siempre retorna 429"
1. Verificar el `plan_tier` del usuario en tabla `users`
2. Verificar uso actual en `user_daily_usage`
3. Verificar fecha: `usage_date` debe ser hoy

### "No se muestra el modal"
1. Verificar que el status code es 429
2. Verificar que `error.detail.error === 'USAGE_LIMIT_REACHED'`
3. Verificar console.log del error completo

---

## 📞 Contacto

Para cualquier duda sobre la integración:
- **Backend:** Jorge (rate limits, tracking)
- **Frontend:** Luis (modal, UX)
- **Database:** Ver `app/migrations/rate_limits.sql`

---

**¡Listo! 💜 Sophia ahora tiene límites gentiles y amables.**

