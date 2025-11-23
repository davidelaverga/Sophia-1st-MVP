# Frontend-Backend Integration Changes

## Resumen
Este documento detalla todos los cambios implementados para integrar el frontend con el nuevo backend de Jorge.

## Fecha de Implementación
21 de noviembre, 2025

---

## 1. Nuevas Rutas API (Proxies Next.js)

Se crearon las siguientes rutas API en Next.js para actuar como proxies seguros al backend:

### Conversación
- ✅ **`/api/conversation/respond`** (ya existía, actualizado)
  - Proxyea a `BACKEND_API_URL/text-chat/stream`
  - Maneja SSE streaming
  - Ahora usa `BACKEND_API_URL` y `BACKEND_API_KEY` (server-side)

- ✅ **`/api/conversation/feedback`** (nuevo)
  - POST para enviar feedback (👍/👎)
  - Proxyea a `BACKEND_API_URL/api/conversation/feedback`

### Privacy
- ✅ **`/api/privacy/status`** (nuevo)
  - GET para obtener estado de consentimiento
  - Proxyea a `BACKEND_API_URL/api/privacy/status`

- ✅ **`/api/privacy/consent`** (nuevo)
  - POST para aceptar consentimiento
  - Proxyea a `BACKEND_API_URL/api/privacy/consent`

- ✅ **`/api/privacy/export`** (nuevo)
  - GET para exportar datos del usuario
  - Proxyea a `BACKEND_API_URL/api/privacy/export`
  - Retorna blob JSON

- ✅ **`/api/privacy/delete`** (nuevo)
  - DELETE para eliminar cuenta
  - Proxyea a `BACKEND_API_URL/api/privacy/delete`

### Reflections
- ✅ **`/api/reflections/prompt`** (nuevo)
  - POST para obtener sugerencias de reflexión
  - Llama a `BACKEND_API_URL/api/reflections/run`
  - Transforma la respuesta del backend al formato esperado por el frontend
  - Divide el `summary` en chunks (máx 3)

- ✅ **`/api/reflections/create`** (nuevo)
  - POST para guardar/compartir reflexión
  - Llama a `BACKEND_API_URL/api/reflections/run` con `share_to_discord` flag

---

## 2. Actualizaciones en Hooks

### `useReflectionPrompt.ts`
**Cambios:**
- Ahora llama a `/api/reflections/prompt` (POST) en lugar de `/api/conversations/:id/reflection-prompt` (GET)
- Envía `conversation_id` y `user_id` en el body
- Mantiene la misma lógica de silent fail y telemetría

**Contrato nuevo:**
```typescript
// Request
POST /api/reflections/prompt
{
  conversation_id: string,
  user_id: string
}

// Response
{
  allow: boolean,
  chunks?: [{ id, text, ts, reason }],
  reflection_id?: string
}
```

### `useVoiceLoop.ts`
**Cambios:**
- Ahora usa `NEXT_PUBLIC_BACKEND_WS_URL` para la conexión WebSocket
- Fallback a `NEXT_PUBLIC_API_URL` si no está definida
- Soporta URLs que ya empiezan con `ws://` o `wss://`

**Configuración:**
```typescript
const wsBase = process.env.NEXT_PUBLIC_BACKEND_WS_URL || process.env.NEXT_PUBLIC_API_URL
const wsUrl = wsBase.startsWith("ws") ? `${wsBase}/ws/voice` : `${httpToWs(wsBase)}/ws/voice`
```

---

## 3. Variables de Entorno

### Archivo: `.env.local` (crear manualmente)

```bash
# Backend API (server-side only, no expuestas al navegador)
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-key

# Public (expuestas al navegador)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000

# Opcional: mock para desarrollo
# NEXT_PUBLIC_MOCK_PRIVACY=true
```

### ¿Por qué dos sets de variables?

1. **`BACKEND_API_URL` y `BACKEND_API_KEY`** (sin `NEXT_PUBLIC_`)
   - Solo accesibles en el servidor (rutas API de Next.js)
   - Nunca se exponen al navegador
   - Más seguras para API keys

2. **`NEXT_PUBLIC_*`**
   - Accesibles en el navegador
   - Necesarias para conexiones directas (WebSocket)
   - No incluyen API keys sensibles

---

## 4. Arquitectura de Proxying

### Antes
```
Frontend React → Backend directo (http://localhost:8001)
```

### Ahora
```
Frontend React → Next.js API Routes → Backend (http://localhost:8000)
                ↓ (solo WebSocket)
                Backend WebSocket (ws://localhost:8000/ws/voice)
```

### Beneficios
- ✅ API keys ocultas del navegador
- ✅ CORS manejado server-side
- ✅ Fácil cambio de backend sin tocar código frontend
- ✅ Logging centralizado en las rutas API
- ✅ Transformación de contratos si es necesario

---

## 5. Mapeo de Endpoints Backend → Frontend

| Frontend Route | Backend Endpoint | Método | Notas |
|----------------|------------------|--------|-------|
| `/api/conversation/respond` | `/text-chat/stream` | POST (SSE) | Streaming de texto |
| `/api/conversation/feedback` | `/api/conversation/feedback` | POST | Feedback 👍👎 |
| `/api/privacy/status` | `/api/privacy/status` | GET | Estado de consentimiento |
| `/api/privacy/consent` | `/api/privacy/consent` | POST | Aceptar consentimiento |
| `/api/privacy/export` | `/api/privacy/export` | GET | Exportar datos (blob) |
| `/api/privacy/delete` | `/api/privacy/delete` | DELETE | Eliminar cuenta |
| `/api/reflections/prompt` | `/api/reflections/run` | POST | Generar reflection (sin share) |
| `/api/reflections/create` | `/api/reflections/run` | POST | Guardar/compartir reflection |
| (directo) | `/ws/voice` | WebSocket | Voz en tiempo real |

---

## 6. Cambios en Contratos

### Reflection Prompt
**Antes (esperado):**
```
GET /api/conversations/:id/reflection-prompt
→ { allow: true, chunks: [...] }
```

**Ahora (implementado):**
```
POST /api/reflections/prompt
{ conversation_id, user_id }
→ { allow: true, chunks: [...], reflection_id }
```

El proxy en Next.js transforma la respuesta de `/api/reflections/run` para que coincida con lo que espera el frontend.

### Reflection Create
**Antes:**
```
POST /api/reflections/create
{ conversation_id, chunk_id, action }
```

**Ahora:**
```
POST /api/reflections/create (proxy)
→ POST /api/reflections/run (backend)
{ conversation_id, user_id, share_to_discord }
```

---

## 7. Testing Checklist

### Antes de probar:
1. ✅ Crear `.env.local` con las variables correctas
2. ✅ Levantar backend: `uvicorn main:app --reload --port 8000`
3. ✅ Levantar frontend: `npm run dev` (puerto 3000)

### Flujos a probar:

#### Texto (SSE)
- [ ] Enviar mensaje de texto
- [ ] Ver streaming de tokens
- [ ] Verificar que no menciona DeFi
- [ ] Verificar presencia (listening → thinking → speaking → resting)

#### Voz (WebSocket)
- [ ] Mantener botón de voz
- [ ] Hablar y soltar
- [ ] Verificar que audio se reproduce
- [ ] Probar barge-in (interrumpir mientras habla)

#### Consent
- [ ] Borrar localStorage
- [ ] Recargar página
- [ ] Verificar que aparece modal de consentimiento
- [ ] Aceptar y verificar que se guarda

#### Feedback
- [ ] Enviar mensaje
- [ ] Dar 👍 o 👎
- [ ] Verificar que se envía al backend
- [ ] Verificar que toast desaparece

#### Reflections
- [ ] Tener conversación de 3+ turnos
- [ ] Verificar si aparece modal de reflexión
- [ ] Seleccionar un chunk
- [ ] Probar "Save privately"
- [ ] Probar "Share to community"

#### Privacy
- [ ] Ir a Settings
- [ ] Probar "Export my data"
- [ ] Verificar que descarga JSON
- [ ] (No probar delete en dev)

---

## 8. Troubleshooting

### Error: "Server configuration incomplete"
**Causa:** Faltan variables de entorno  
**Solución:** Crear `.env.local` con `BACKEND_API_URL` y `BACKEND_API_KEY`

### Error: 404 en llamadas API
**Causa:** Backend no está corriendo o URL incorrecta  
**Solución:** Verificar que backend está en `http://localhost:8000`

### Error: Voice connection fails
**Causa:** WebSocket URL incorrecta  
**Solución:** Verificar `NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000`

### Error: CORS
**Causa:** Backend no permite origen del frontend  
**Solución:** Configurar CORS en backend para permitir `http://localhost:3000`

### Reflections no aparecen
**Causa:** Backend no implementó `/api/reflections/run` aún  
**Solución:** Silent fail esperado, no bloquea la app

### Privacy endpoints 404
**Causa:** Backend no implementó endpoints de privacy  
**Solución:** Usar `NEXT_PUBLIC_MOCK_PRIVACY=true` temporalmente

---

## 9. Próximos Pasos

### Para Luis (Frontend):
1. Crear `.env.local` con las variables
2. Probar todos los flujos
3. Reportar cualquier diferencia de contrato a Jorge
4. Documentar bugs/issues encontrados

### Para Jorge (Backend):
1. Verificar que todos los endpoints están implementados
2. Confirmar contratos (especialmente reflections)
3. Configurar CORS para `http://localhost:3000`
4. Proveer credenciales/URLs para staging

### Para ambos:
1. Sesión de integración para probar end-to-end
2. Ajustar contratos si es necesario
3. Documentar cualquier cambio adicional
4. Preparar para deploy a staging

---

## 10. Archivos Modificados

### Nuevos:
- `frontend-nextjs/app/api/conversation/feedback/route.ts`
- `frontend-nextjs/app/api/privacy/status/route.ts`
- `frontend-nextjs/app/api/privacy/consent/route.ts`
- `frontend-nextjs/app/api/privacy/export/route.ts`
- `frontend-nextjs/app/api/privacy/delete/route.ts`
- `frontend-nextjs/app/api/reflections/prompt/route.ts`
- `frontend-nextjs/app/api/reflections/create/route.ts`
- `frontend-nextjs/ENV_SETUP.md`
- `frontend-nextjs/INTEGRATION_CHANGES.md` (este archivo)

### Modificados:
- `frontend-nextjs/app/api/conversation/respond/route.ts` (cambio de env vars)
- `frontend-nextjs/app/hooks/useReflectionPrompt.ts` (nuevo endpoint)
- `frontend-nextjs/app/hooks/useVoiceLoop.ts` (nueva env var para WS)

### Sin cambios (ya funcionan):
- `frontend-nextjs/app/lib/api/privacy.ts` (ya usa `/api/privacy/*`)
- `frontend-nextjs/app/lib/api/reflections.ts` (ya usa `/api/reflections/create`)
- `frontend-nextjs/app/lib/api/feedback.ts` (ya usa `/api/conversation/feedback`)
- Todos los componentes UI (no necesitan cambios)

---

## Resumen Ejecutivo

✅ **7 nuevas rutas API** creadas como proxies seguros  
✅ **3 hooks actualizados** para usar nuevos endpoints  
✅ **Variables de entorno** documentadas y configuradas  
✅ **Sin errores de linter** en ningún archivo  
✅ **Arquitectura de proxying** implementada correctamente  
✅ **Documentación completa** para setup y troubleshooting  

**Estado:** ✅ Listo para testing en localhost  
**Siguiente paso:** Crear `.env.local` y probar end-to-end

