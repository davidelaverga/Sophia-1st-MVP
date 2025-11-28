# Completar el Merge de feature/rate_payments

## Situación Actual

El merge se intentó pero los cambios no se prepararon (staged) correctamente. Necesitas:

1. Limpiar archivos de build (.next/)
2. Agregar los archivos importantes del merge
3. Hacer el commit

---

## Solución Paso a Paso

### Paso 1: Limpiar archivos de build

```powershell
# Descartar cambios en archivos de build (no deberían estar en git)
git restore frontend-nextjs/.next/
```

---

### Paso 2: Ver qué archivos cambiaron del merge

```powershell
# Ver archivos modificados
git status --short

# Ver diferencias con la rama remota
git diff origin/feature/rate_payments --name-only
```

---

### Paso 3: Agregar los archivos importantes del merge

```powershell
# Agregar los archivos de código que cambiaron
git add frontend-nextjs/app/components/ConversationView.tsx
git add frontend-nextjs/app/components/VoiceRecorder.tsx
git add frontend-nextjs/app/hooks/useVoiceLoop.ts
git add frontend-nextjs/app/components/SettingsSheet.tsx
git add frontend-nextjs/app/globals.css
git add frontend-nextjs/app/layout.tsx

# Si hay archivos nuevos importantes (como ThemeBootstrap.tsx)
git add frontend-nextjs/app/ThemeBootstrap.tsx
```

---

### Paso 4: Manejar archivos eliminados (opcional)

Si los archivos .md eliminados son documentación temporal que ya no necesitas:

```powershell
# Agregar las eliminaciones al commit
git add -u
```

O si quieres mantenerlos:

```powershell
# Restaurar los archivos eliminados
git restore CURRENT_SESSION_CONTEXT.md DEMO_WAVEFORM_RAPIDO.md
# (etc para los otros)
```

---

### Paso 5: Hacer el commit del merge

```powershell
git commit -m "Merge feature/rate_payments: Integrar fix ws voice y otros cambios"
```

---

## Solución Rápida (Todo en uno)

```powershell
# 1. Limpiar archivos de build
git restore frontend-nextjs/.next/

# 2. Agregar archivos importantes del merge
git add frontend-nextjs/app/components/ConversationView.tsx
git add frontend-nextjs/app/components/VoiceRecorder.tsx
git add frontend-nextjs/app/hooks/useVoiceLoop.ts
git add frontend-nextjs/app/components/SettingsSheet.tsx
git add frontend-nextjs/app/globals.css
git add frontend-nextjs/app/layout.tsx
git add frontend-nextjs/app/ThemeBootstrap.tsx

# 3. Agregar eliminaciones de archivos .md (si los quieres eliminar)
git add -u

# 4. Hacer commit
git commit -m "Merge feature/rate_payments: Integrar fix ws voice y otros cambios"
```

---

## Verificar que funcionó

```powershell
# Ver si el commit "fix ws voice" está en el historial
git log HEAD --oneline | Select-String "fix ws voice"

# Ver los últimos commits
git log --oneline -5

# Ver el estado final
git status
```

---

## Nota sobre archivos .next/

Los archivos en `frontend-nextjs/.next/` son archivos de build generados automáticamente. **NO deberían estar en git**. 

Si estos archivos están siendo rastreados, deberías:
1. Asegurarte de que `.gitignore` tenga `.next/`
2. Eliminarlos del tracking de git:
   ```powershell
   git rm -r --cached frontend-nextjs/.next/
   git commit -m "Remove .next/ from git tracking"
   ```

---

## Si prefieres hacer el merge de nuevo desde cero

```powershell
# 1. Cancelar el merge actual (si hay uno en progreso)
git merge --abort

# 2. Guardar tus cambios locales
git stash

# 3. Hacer el merge limpio
git merge origin/feature/rate_payments

# 4. Aplicar tus cambios guardados
git stash pop
```

