# Integration Checklist - Sophia Frontend ↔ Backend

## 📋 Pre-requisitos

- [ ] Backend de Jorge bajado y actualizado (`git pull`)
- [ ] Frontend actualizado con los cambios de integración
- [ ] Node.js y npm instalados
- [ ] Python y entorno virtual configurado

---

## 🔧 Setup (Hacer UNA vez)

### Backend
- [ ] Crear/activar entorno virtual: `.\.venv\Scripts\activate`
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Verificar que `main.py` tiene configuración CORS para `localhost:3000`

### Frontend
- [ ] `cd frontend-nextjs`
- [ ] Instalar dependencias: `npm install`
- [ ] **IMPORTANTE:** Crear archivo `.env.local` con:
  ```bash
  BACKEND_API_URL=http://localhost:8000
  BACKEND_API_KEY=dev-key
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000
  ```

---

## 🚀 Testing (Cada sesión)

### 1. Levantar Servicios

Terminal 1 (Backend):
```bash
cd C:/Users/zerof/OneDrive/Documents/GitHub/Sophia-1st-MVP
.\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```
- [ ] Backend corriendo en `http://localhost:8000`
- [ ] Ver logs sin errores

Terminal 2 (Frontend):
```bash
cd C:/Users/zerof/OneDrive/Documents/GitHub/Sophia-1st-MVP/frontend-nextjs
npm run dev
```
- [ ] Frontend corriendo en `http://localhost:3000`
- [ ] Ver logs sin errores de compilación

---

### 2. Test: Consent Gate 🔒

- [ ] Abrir `http://localhost:3000`
- [ ] Aparece modal de consentimiento
- [ ] Leer el texto (debe estar en inglés)
- [ ] Click en "I understand and accept"
- [ ] Modal desaparece
- [ ] Se ve la interfaz principal

**Si falla:**
- Abrir DevTools → Network → Ver llamada a `/api/privacy/status`
- Si 404: Backend no tiene endpoint, usar `NEXT_PUBLIC_MOCK_PRIVACY=true` en `.env.local`

---

### 3. Test: Texto (SSE Streaming) 💬

- [ ] Escribir mensaje: "Hi Sophia, how are you?"
- [ ] Click Send o Enter
- [ ] Ver indicador de presencia: Listening → Thinking → Speaking
- [ ] Ver texto aparecer token por token (streaming)
- [ ] Respuesta NO menciona DeFi
- [ ] Respuesta es cálida y empática

**DevTools Check:**
- Network → `/api/conversation/respond` → Status 200
- Ver eventos SSE: `meta`, `token`, `done`

**Si falla:**
- Ver Console para errores
- Verificar que backend responde en `/text-chat/stream`

---

### 4. Test: Voz (WebSocket) 🎤

- [ ] Ver botón morado con ícono de micrófono
- [ ] Mantener presionado el botón
- [ ] Navegador pide permiso de micrófono (primera vez)
- [ ] Aceptar permiso
- [ ] Hablar: "Hello Sophia, can you hear me?"
- [ ] Soltar el botón
- [ ] Ver estado cambiar: Listening → Thinking → Speaking
- [ ] Escuchar respuesta de audio
- [ ] Audio suena natural (TTS)

**DevTools Check:**
- Network → WS → Ver conexión a `ws://localhost:8000/ws/voice`
- Ver mensajes binarios (audio PCM) subiendo
- Ver mensajes JSON bajando (tokens, audio)

**Si falla:**
- Ver Console para errores de WebSocket
- Verificar que tienes micrófono conectado
- Verificar permisos del navegador

---

### 5. Test: Barge-in (Interrumpir) ⚡

- [ ] Iniciar voz y hacer una pregunta larga
- [ ] Mientras Sophia está hablando (audio reproduciéndose)
- [ ] Click en botón "Interrupt" o mantener micrófono de nuevo
- [ ] Audio de Sophia se detiene inmediatamente
- [ ] Puedes hablar de nuevo

**Esperado:**
- Latencia de barge-in < 200ms
- Sin glitches de audio

---

### 6. Test: Feedback Inline 👍👎

- [ ] Enviar mensaje de texto
- [ ] Esperar respuesta de Sophia
- [ ] Ver tira de feedback debajo del mensaje
- [ ] Click en 👍
- [ ] Ver confirmación visual
- [ ] Feedback desaparece

**DevTools Check:**
- Network → `/api/conversation/feedback` → Status 200

**Si falla con 404:**
- Es esperado si backend no tiene endpoint
- Debe aparecer botón "Skip feedback"
- Click en Skip y continuar

---

### 7. Test: Feedback Toast (Fallback) 🍞

- [ ] Tener conversación de 2-3 turnos
- [ ] Si NO apareció feedback inline
- [ ] Debe aparecer toast en la parte inferior: "How did that feel?"
- [ ] Click en 👍 o 👎
- [ ] Toast desaparece

**O bien:**
- [ ] Click en "Skip"
- [ ] Toast desaparece sin enviar

---

### 8. Test: Reflections (Post-conversación) 💭

- [ ] Tener conversación significativa (5+ turnos)
- [ ] Después de un turno emocional
- [ ] Puede aparecer modal de reflexión
- [ ] Ver 3 opciones de frases
- [ ] Seleccionar una
- [ ] Click "Save privately" o "Share with community"
- [ ] Modal desaparece
- [ ] Ver confirmación

**Nota:**
- Si NO aparece: es esperado (backend decide cuándo)
- No es un error, es gating inteligente

**Si aparece error:**
- Debe haber botón "Not now"
- Click y continuar

---

### 9. Test: Privacy Settings ⚙️

- [ ] Click en botón "Settings" (arriba derecha)
- [ ] Se abre panel lateral
- [ ] Ver sección "Privacy & Data"
- [ ] Click "Export my data"
- [ ] Esperar 2-3 segundos
- [ ] Descarga archivo `sophia-data.json`
- [ ] Abrir JSON y verificar contenido

**NO probar "Delete my account" en dev**

---

### 10. Test: Responsiveness 📱

- [ ] Abrir DevTools
- [ ] Toggle device toolbar (Ctrl+Shift+M)
- [ ] Probar en:
  - [ ] iPhone SE (375px)
  - [ ] Galaxy Fold (280px)
  - [ ] iPad (768px)
  - [ ] Desktop (1920px)

**Verificar:**
- Sin scroll horizontal
- Botones accesibles
- Texto legible
- Safe areas respetadas

---

### 11. Test: Presence Indicators 🟣

Durante cualquier interacción, verificar que el indicador de presencia (arriba) muestra:

- [ ] **Resting** (inicial): punto morado suave
- [ ] **Listening** (mientras hablas): pulso morado
- [ ] **Thinking** (procesando): animación sutil
- [ ] **Reflecting** (buscando memoria): texto "Reflecting..."
- [ ] **Speaking** (reproduciendo audio): indicador activo

**No debe:**
- Parpadear rápidamente (anti-flicker funciona)
- Quedarse stuck en un estado

---

### 12. Test: Error Handling 🚨

#### Backend caído
- [ ] Detener backend (Ctrl+C)
- [ ] Enviar mensaje en frontend
- [ ] Ver error amigable (no crash)
- [ ] Poder reintentar

#### Sin internet (simular)
- [ ] DevTools → Network → Offline
- [ ] Enviar mensaje
- [ ] Ver error de conexión
- [ ] Volver Online
- [ ] Poder continuar

#### Micrófono denegado
- [ ] Settings del navegador → Bloquear micrófono
- [ ] Intentar usar voz
- [ ] Ver mensaje: "Microphone access denied"
- [ ] Link para reactivar permisos

---

## 🎯 Criterios de Éxito

### Must Have (Bloqueantes)
- ✅ Texto streaming funciona sin mencionar DeFi
- ✅ Voz conecta y reproduce audio
- ✅ Consent gate bloquea hasta aceptar
- ✅ No hay crashes en flujos principales

### Should Have (Importantes)
- ✅ Feedback se envía correctamente
- ✅ Reflections aparecen cuando corresponde
- ✅ Privacy export funciona
- ✅ Responsive en móviles

### Nice to Have (Mejoras)
- ✅ Barge-in < 200ms
- ✅ Presence indicators fluidos
- ✅ Animaciones suaves
- ✅ Telemetría enviándose

---

## 📝 Reporte de Bugs

Si encuentras algo que no funciona, documenta:

1. **Qué paso estabas probando:** (ej: "Test 4: Voz")
2. **Qué hiciste:** (ej: "Mantuve el botón y hablé")
3. **Qué esperabas:** (ej: "Escuchar respuesta de audio")
4. **Qué pasó:** (ej: "Error: WebSocket connection failed")
5. **Console logs:** (copiar errores de DevTools)
6. **Network tab:** (screenshot de llamadas fallidas)

Enviar a Jorge con tag: `[BUG] Descripción corta`

---

## ✅ Checklist Final

Antes de considerar la integración completa:

- [ ] Todos los tests 1-12 pasaron
- [ ] No hay errores en Console (excepto warnings esperados)
- [ ] No hay errores en Network (excepto 404 documentados)
- [ ] Performance es aceptable (no lag visible)
- [ ] Funciona en Chrome, Firefox y Safari
- [ ] Funciona en móvil (al menos un dispositivo real)

---

## 🚢 Ready for Demo

Cuando todo funcione:

- [ ] Grabar video corto (2-3 min) mostrando:
  - Consent flow
  - Conversación de texto
  - Conversación de voz
  - Feedback
  - Reflection (si aparece)

- [ ] Compartir con Rafael para validación
- [ ] Documentar cualquier limitación conocida
- [ ] Preparar talking points para demo

---

**Última actualización:** 21 Nov 2025  
**Responsable:** Luis (Frontend)  
**Coordinación con:** Jorge (Backend)

