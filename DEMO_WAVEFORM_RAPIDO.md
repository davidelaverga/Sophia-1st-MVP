# 🎵 Demo Rápido del Waveform - Guía Express

## ⚡ Preparación (2 minutos)

### 1. Levanta el Frontend
```bash
cd frontend-nextjs
npm run dev
```

### 2. Abre el Navegador
```
http://localhost:3000
```

### 3. Acepta Permisos
- Si te pide consentimiento, acepta
- Si te pide permisos de micrófono, acepta

---

## 🎬 Demo al Cliente (30 segundos)

### Paso 1: Navega al Panel de Voz
- Scroll down hasta "Live voice space"
- Muestra el estado idle (barras pequeñas en morado)

### Paso 2: Activa el Micrófono
- **Presiona y mantén** el botón morado del micrófono
- **Habla**: "Hello Sophia, how are you today?"
- **Observa**: Las barras reaccionan a tu voz en tiempo real

### Paso 3: Suelta y Espera
- **Suelta** el botón
- Espera a que Sophia responda
- **Observa**: Las barras cambian a animación de onda suave

---

## 🎯 Qué Destacar

1. **"Mira cómo las barras reaccionan a mi voz en tiempo real"**
   - Habla más fuerte → barras más altas
   - Habla más suave → barras más bajas

2. **"Cuando Sophia responde, la animación cambia"**
   - Onda suave y fluida
   - Color más tenue
   - Sensación de conversación bidireccional

3. **"Usa los colores de Sophia para mantener cohesión visual"**
   - Morado característico
   - Gradientes suaves
   - Estética "calm and wise"

---

## 🐛 Si Algo Falla

### Problema: "No veo el waveform"
**Solución**: Reinicia el frontend (Ctrl+C y `npm run dev`)

### Problema: "Las barras no se mueven cuando hablo"
**Solución**: 
1. Verifica permisos de micrófono en el navegador
2. Asegúrate de tener un micrófono conectado
3. Revisa la consola del navegador (F12)

### Problema: "Sophia no responde"
**Solución**: 
1. Verifica que el backend esté corriendo
2. Revisa el archivo `.env.local` (debe tener `BACKEND_API_URL`)
3. Esto es independiente del waveform (el waveform funciona sin backend)

---

## 📸 Screenshots Recomendados

Si vas a hacer slides:

1. **Idle** - Captura con barras en reposo
2. **Hablando** - Captura mientras hablas (barras altas)
3. **Sophia hablando** - Captura la animación de onda
4. **Móvil** - Captura en DevTools (iPhone SE o similar)

---

## 💬 Frases Clave para el Cliente

> "Implementamos el waveform que solicitaste. Usa datos reales de audio y se adapta al contexto de la conversación."

> "Esto hace que Sophia se sienta más viva y reactiva, sin perder su personalidad calmada."

> "Es el mismo estándar que usan Siri, Google Assistant y ChatGPT Voice."

---

## ✅ Checklist Final

Antes de la demo:
- [ ] Frontend corriendo
- [ ] Navegador abierto en `localhost:3000`
- [ ] Permisos de micrófono otorgados
- [ ] Micrófono/audífonos conectados
- [ ] Probado una vez (para estar seguro)

---

## 🎉 ¡Listo!

**Todo está implementado y funcionando.**

Si el cliente pregunta por mejoras futuras, menciona:
- Colores por emoción
- Bandas de frecuencia
- Toggle en settings

**¡Mucha suerte en tu presentación!** 🚀


