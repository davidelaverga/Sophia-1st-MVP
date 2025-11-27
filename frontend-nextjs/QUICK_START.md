# Quick Start - Testing Integration

## Paso 1: Crear `.env.local`

Crea el archivo `frontend-nextjs/.env.local` con este contenido:

```bash
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-key
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000
```

## Paso 2: Levantar Backend

En la raíz del proyecto:

```bash
# Activar entorno virtual (si es necesario)
.\.venv\Scripts\activate

# Levantar backend
uvicorn main:app --reload --port 8000
```

Deberías ver:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Paso 3: Levantar Frontend

En otra terminal, dentro de `frontend-nextjs`:

```bash
npm run dev
```

Deberías ver:
```
- Local:   http://localhost:3000
```

## Paso 4: Probar en el Navegador

Abre `http://localhost:3000` y prueba:

### ✅ Consent Gate
- Debería aparecer el modal de consentimiento
- Acepta y verifica que desaparece

### ✅ Texto
- Envía un mensaje de texto
- Verifica que la respuesta NO menciona DeFi
- Observa el streaming de tokens

### ✅ Voz
- Mantén presionado el botón de micrófono
- Habla algo
- Suelta el botón
- Verifica que Sophia responde con audio

### ✅ Feedback
- Después de un mensaje, da 👍 o 👎
- Verifica que el feedback se envía

### ✅ Settings
- Abre Settings
- Prueba "Export my data"
- Verifica que descarga un JSON

## Problemas Comunes

### Backend no conecta
```bash
# Verifica que el backend está corriendo
curl http://localhost:8000/health
```

### Frontend no encuentra backend
- Verifica que `.env.local` existe y tiene las variables correctas
- Reinicia el frontend (`Ctrl+C` y `npm run dev` de nuevo)

### Voice no funciona
- Verifica que tienes micrófono conectado
- Verifica que el navegador tiene permisos de micrófono
- Abre DevTools → Console para ver errores

### CORS errors
- El backend debe permitir `http://localhost:3000`
- Verifica configuración CORS en `main.py`

## Siguiente Paso

Si todo funciona, revisa `INTEGRATION_CHANGES.md` para detalles completos de la implementación.

