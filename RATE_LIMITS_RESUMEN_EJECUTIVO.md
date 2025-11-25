# 💜 Rate Limits para Sophia - Resumen Ejecutivo

## ✅ ¿Qué se hizo?

Se integró un **sistema de rate limiting gentil y amable** en el backend de Sophia que:

1. **No rompe nada** - Es completamente opcional (solo funciona si se envía `user_id`)
2. **Responde con calidez** - Mensajes amables cuando se alcanza el límite
3. **Trackea automáticamente** - Registra uso de voz y texto después de cada interacción
4. **Funciona en todos lados** - Chat de texto, voz y WebSocket

---

## 📦 Archivos Agregados

### Backend (Solo Backend - Tu Frontend Está Intacto)

```
app/
├── services/
│   ├── rate_limits.py          ← Servicio principal de rate limiting
│   └── plan_config.py          ← Configuración de planes (FREE, SUPPORTER, etc)
├── routers/
│   ├── usage_router.py         ← API para consultar uso actual
│   └── stripe_router.py        ← Placeholder para Stripe (futuro)
└── migrations/
    └── rate_limits.sql         ← SQL para crear tablas en Supabase

main.py                         ← Modificado: integración en endpoints

RATE_LIMITS_INTEGRATION_GUIDE.md  ← Guía completa para el equipo
```

---

## 🎯 Cómo Funciona (Simple)

### 1. **Frontend envía `user_id` (opcional)**
```json
{
  "message": "Hola Sophia",
  "user_id": "uuid-del-usuario"  // ← Opcional
}
```

### 2. **Backend verifica límites ANTES de procesar**
- Si no hay `user_id` → Todo funciona como antes
- Si hay `user_id` → Verifica si tiene límites disponibles

### 3. **Si se alcanza el límite → Respuesta gentil (HTTP 429)**
```json
{
  "detail": {
    "error": "USAGE_LIMIT_REACHED",
    "reason": "voice",
    "title": "You've reached today's free voice limit 💜",
    "body": "Sophia is still in her early days..."
  }
}
```

### 4. **Si todo OK → Procesa y trackea uso automáticamente**

---

## 📊 Planes Configurados

| Plan | Voz/Día | Texto/Día | Reflections/Mes |
|------|---------|-----------|-----------------|
| **FREE** | 10 min | 40 msgs | 4 cards |
| **SUPPORTER** | 60 min | 200 msgs | 30 cards |
| **FOUNDING_SUPPORTER** | 120 min | 400 msgs | 100 cards |

---

## 🔧 Endpoints Modificados

### `/text-chat` (Chat de Texto)
- **Nuevo parámetro:** `user_id` (opcional)
- **Verifica:** Límite de mensajes de texto
- **Trackea:** +1 mensaje después de procesar

### `/defi-chat` (Chat de Voz)
- **Nuevo parámetro:** `user_id` (opcional, form data)
- **Verifica:** Límite de segundos de voz
- **Trackea:** ~3 segundos después de procesar

### `/ws/voice` (WebSocket)
- **Nuevo query param:** `?user_id=xxx` (opcional)
- **Verifica:** Límite de segundos de voz por turno
- **Trackea:** Duración real del audio después de procesar
- **Nota:** NO cierra la conexión, solo detiene ese turno

---

## 🆕 Nuevos Endpoints

### `GET /api/usage/limits?user_id=xxx`
Consulta el uso actual del usuario:
```json
{
  "user_id": "xxx",
  "plan_tier": "FREE",
  "daily_voice": { "used": 245, "limit": 600, "remaining": 355 },
  "daily_text": { "used": 12, "limit": 40, "remaining": 28 },
  "monthly_reflections": { "used": 2, "limit": 4, "remaining": 2 }
}
```

### `GET /api/usage/plans`
Lista todos los planes disponibles

### `POST /api/stripe/webhook`
Placeholder para webhooks de Stripe (futuro)

---

## 🗄️ Base de Datos

### Nuevas Tablas (SQL en `app/migrations/rate_limits.sql`)

1. **`user_daily_usage`**
   - Trackea uso diario de voz y texto por usuario
   - Se resetea automáticamente cada día

2. **`reflection_cards`** (ya existe, solo se consulta)
   - Trackea Reflection Cards mensuales

3. **Función `upsert_user_daily_usage`**
   - Actualiza uso de forma atómica (evita race conditions)

### Para Aplicar
```sql
-- En Supabase Dashboard > SQL Editor
-- Copiar y ejecutar: app/migrations/rate_limits.sql
```

---

## 🚀 Próximos Pasos

### Backend (Ya Listo ✅)
- ✅ Servicios de rate limiting
- ✅ Integración en endpoints
- ✅ APIs de consulta
- ⏳ **Pendiente:** Ejecutar SQL migration en Supabase

### Frontend (Para Luis)
1. **Obtener `user_id`** del usuario autenticado
2. **Agregar `user_id`** a las peticiones (opcional)
3. **Crear modal** para mostrar cuando se alcanza el límite (HTTP 429)
4. **Manejar error** en WebSocket con mensaje gentil

Ver guía completa en: `RATE_LIMITS_INTEGRATION_GUIDE.md`

---

## 🎨 Ejemplo de Integración Frontend

```typescript
// 1. Obtener user_id
const { data: { user } } = await supabase.auth.getUser();
const userId = user?.id;

// 2. Enviar en petición
const response = await fetch('/api/conversation/respond', {
  method: 'POST',
  body: JSON.stringify({
    message: userMessage,
    user_id: userId,  // ← Agregar aquí
  }),
});

// 3. Manejar error 429
if (response.status === 429) {
  const error = await response.json();
  if (error.detail?.error === 'USAGE_LIMIT_REACHED') {
    showUsageLimitModal(error.detail);  // ← Mostrar modal gentil
  }
}
```

---

## 💡 Ventajas de Este Approach

### ✅ No Rompe Nada
- Si no se envía `user_id`, todo funciona como antes
- Rollout gradual: activar solo para usuarios autenticados

### ✅ Gentil y Amable
- Mensajes cálidos en lugar de errores fríos
- Explica por qué existe el límite
- Ofrece opciones sin presión

### ✅ Robusto
- Tracking en "best effort" (no bloquea si falla)
- Límites se resetean automáticamente
- Funciona con voz y texto

### ✅ Escalable
- Fácil agregar nuevos planes
- Fácil cambiar límites (solo editar `plan_config.py`)
- Preparado para Stripe

---

## 📞 Siguiente Reunión

### Para Discutir:
1. ¿Cuándo ejecutamos la migración SQL en Supabase?
2. ¿Cuándo integra Luis el `user_id` en el frontend?
3. ¿Diseño del modal de límite alcanzado?
4. ¿Cuándo activamos Stripe?

---

## 🎯 TL;DR

**Backend está listo.** Solo falta:
1. Ejecutar SQL en Supabase
2. Frontend agregue `user_id` a las peticiones
3. Frontend maneje error 429 con modal gentil

**Tu frontend está 100% intacto.** Todo es opcional y retrocompatible.

---

**¿Preguntas? Ver:** `RATE_LIMITS_INTEGRATION_GUIDE.md` 💜

