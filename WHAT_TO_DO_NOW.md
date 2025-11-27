# ¿Qué Hacer Ahora? - Guía para Luis

## 🎯 Resumen Ejecutivo

**Todo el código está listo.** Solo necesitas:
1. Crear un archivo de configuración (`.env.local`)
2. Levantar backend y frontend
3. Probar que todo funciona

---

## 📝 Paso 1: Crear `.env.local`

### Ubicación
```
C:\Users\zerof\OneDrive\Documents\GitHub\Sophia-1st-MVP\frontend-nextjs\.env.local
```

### Contenido (copiar y pegar)
```bash
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-key
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000
```

### Cómo crearlo
**Opción A - Desde VS Code:**
1. Abrir carpeta `frontend-nextjs`
2. Click derecho → New File
3. Nombrar: `.env.local`
4. Pegar el contenido de arriba
5. Guardar (Ctrl+S)

**Opción B - Desde PowerShell:**
```powershell
cd C:\Users\zerof\OneDrive\Documents\GitHub\Sophia-1st-MVP\frontend-nextjs
@"
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-key
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000
"@ | Out-File -FilePath .env.local -Encoding utf8
```

---

## 🚀 Paso 2: Levantar Backend

### Terminal 1 (PowerShell)
```powershell
cd C:\Users\zerof\OneDrive\Documents\GitHub\Sophia-1st-MVP
.\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### Verificar que funciona
Deberías ver algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Test rápido
Abrir en navegador: `http://localhost:8000/docs`  
Deberías ver la documentación de FastAPI.

---

## 🎨 Paso 3: Levantar Frontend

### Terminal 2 (PowerShell - nueva terminal)
```powershell
cd C:\Users\zerof\OneDrive\Documents\GitHub\Sophia-1st-MVP\frontend-nextjs
npm run dev
```

### Verificar que funciona
Deberías ver algo como:
```
- Local:        http://localhost:3000
- Network:      http://192.168.x.x:3000

✓ Ready in 2.5s
```

### Test rápido
Abrir en navegador: `http://localhost:3000`  
Deberías ver el modal de consentimiento de Sophia.

---

## ✅ Paso 4: Testing Básico

### Test 1: Consent (30 segundos)
1. Abrir `http://localhost:3000`
2. Ver modal de consentimiento
3. Click "I understand and accept"
4. Modal desaparece
5. ✅ Si funciona, continuar

### Test 2: Texto (1 minuto)
1. Escribir: "Hi Sophia, how are you?"
2. Presionar Enter o click Send
3. Ver respuesta aparecer token por token
4. Verificar que NO menciona DeFi
5. ✅ Si funciona, continuar

### Test 3: Voz (2 minutos)
1. Mantener presionado botón morado (micrófono)
2. Permitir acceso al micrófono (si pide)
3. Decir: "Hello Sophia, can you hear me?"
4. Soltar botón
5. Escuchar respuesta de audio
6. ✅ Si funciona, continuar

### Test 4: Feedback (30 segundos)
1. Después de un mensaje de Sophia
2. Ver botones 👍 👎 debajo
3. Click en uno
4. Ver que desaparece
5. ✅ Si funciona, ¡todo listo!

---

## 🐛 Si Algo Falla

### Backend no levanta
**Error:** `Address already in use`
```powershell
# Buscar proceso en puerto 8000
netstat -ano | findstr :8000
# Matar proceso (reemplazar PID con el número que aparece)
taskkill /PID [número] /F
# Intentar de nuevo
uvicorn main:app --reload --port 8000
```

### Frontend no levanta
**Error:** `Port 3000 is already in use`
```powershell
# Buscar proceso en puerto 3000
netstat -ano | findstr :3000
# Matar proceso
taskkill /PID [número] /F
# Intentar de nuevo
npm run dev
```

### "Server configuration incomplete"
**Causa:** No creaste `.env.local` o está mal ubicado  
**Solución:** Verificar que el archivo existe en `frontend-nextjs/.env.local`

### Consent modal no aparece
**Causa:** Backend no tiene endpoint de privacy  
**Solución temporal:** Agregar a `.env.local`:
```bash
NEXT_PUBLIC_MOCK_PRIVACY=true
```
Reiniciar frontend (Ctrl+C y `npm run dev`)

### Voice no funciona
**Causa 1:** No tienes micrófono  
**Solución:** Conectar audífonos con micrófono

**Causa 2:** Permisos denegados  
**Solución:** Chrome → Settings → Privacy → Site Settings → Microphone → Permitir

---

## 📊 Paso 5: Testing Completo (Opcional)

Si quieres hacer testing exhaustivo:

1. Abrir archivo: `INTEGRATION_CHECKLIST.md`
2. Seguir los 12 tests paso a paso
3. Marcar cada checkbox que completes
4. Documentar cualquier problema

---

## 🎥 Paso 6: Demo (Cuando todo funcione)

### Grabar video corto (2-3 minutos)
1. Mostrar consent flow
2. Conversación de texto (2-3 mensajes)
3. Conversación de voz (1 pregunta)
4. Dar feedback
5. Mostrar settings (export data)

### Herramienta recomendada
- Windows: Xbox Game Bar (Win+G → Capture)
- O: OBS Studio (gratis)

---

## 📞 Contacto con Jorge

### Si todo funciona
Mensaje sugerido:
```
Hola Jorge! 👋

Ya probé la integración en localhost y todo funciona:
✅ Texto streaming
✅ Voz con WebSocket
✅ Consent flow
✅ Feedback

¿Cuándo podemos hacer una sesión para probar juntos y validar que 
todo está bien de tu lado también?

Adjunto video de demo.
```

### Si algo no funciona
Mensaje sugerido:
```
Hola Jorge! 👋

Ya probé la integración pero tengo un issue:

**Test:** [nombre del test, ej: "Voz"]
**Qué hice:** [pasos]
**Esperaba:** [resultado esperado]
**Obtuve:** [error o comportamiento]

**Console logs:**
[copiar errores de DevTools]

**Network tab:**
[screenshot de llamada fallida]

¿Puedes revisar el endpoint [nombre]?
```

---

## 📚 Documentos de Referencia

Si necesitas más detalles:

1. **`QUICK_START.md`** - Setup rápido (lo que estás leyendo ahora, versión corta)
2. **`INTEGRATION_CHECKLIST.md`** - Testing exhaustivo (12 tests)
3. **`INTEGRATION_CHANGES.md`** - Cambios técnicos detallados
4. **`ENV_SETUP.md`** - Variables de entorno explicadas
5. **`IMPLEMENTATION_SUMMARY.md`** - Resumen ejecutivo para presentación

---

## ✨ Siguiente Milestone

Cuando todo funcione en localhost:

1. ✅ Commit de tus cambios
2. ✅ Push a tu rama
3. ✅ Crear PR con descripción
4. ✅ Tag a Jorge para review
5. ✅ Coordinar deploy a staging
6. ✅ Preparar demo para Rafael

---

## 🎉 ¡Estás Listo!

Todo el código está implementado y documentado.  
Solo necesitas:
1. Crear `.env.local` (2 minutos)
2. Levantar servicios (1 minuto)
3. Probar (5 minutos)

**Total: ~10 minutos para tener todo funcionando.**

Si tienes dudas, revisa los otros documentos o contacta a Jorge.

---

**¡Éxito con el testing!** 🚀

