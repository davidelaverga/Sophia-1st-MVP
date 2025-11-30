# Comandos para Ver Pushes Recientes

## Ver Pushes de tu Rama Actual

### 1. Ver commits recientes de tu rama remota
```powershell
# Ver los últimos 10 commits de tu rama en el remoto
git log origin/ENHANCE-FE-LE --oneline -10

# O usar el nombre de tu rama actual automáticamente
git log origin/$(git branch --show-current) --oneline -10
```

### 2. Ver commits que has hecho pero NO has pusheado
```powershell
# Ver commits locales que no están en el remoto
git log origin/ENHANCE-FE-LE..HEAD --oneline

# O automáticamente con tu rama actual
git log origin/$(git branch --show-current)..HEAD --oneline
```

### 3. Ver commits que están en el remoto pero NO en tu local
```powershell
# Ver commits remotos que no tienes localmente
git log HEAD..origin/ENHANCE-FE-LE --oneline

# O automáticamente
git log HEAD..origin/$(git branch --show-current) --oneline
```

### 4. Ver historial completo con gráfico
```powershell
# Ver últimos 15 commits con gráfico visual
git log --oneline --graph --all --decorate -15

# Ver solo tu rama y el remoto
git log --oneline --graph origin/ENHANCE-FE-LE HEAD -15
```

### 5. Ver información detallada de commits recientes
```powershell
# Ver últimos 5 commits con detalles (autor, fecha, mensaje)
git log origin/ENHANCE-FE-LE -5 --pretty=format:"%h - %an, %ar : %s"

# Ver con más información
git log origin/ENHANCE-FE-LE -5 --pretty=format:"%h | %an | %ad | %s" --date=short
```

### 6. Ver diferencias entre local y remoto
```powershell
# Ver qué commits están en remoto pero no en local
git fetch origin
git log HEAD..origin/ENHANCE-FE-LE --oneline

# Ver qué commits están en local pero no en remoto
git log origin/ENHANCE-FE-LE..HEAD --oneline
```

## Comandos Útiles Adicionales

### Ver el último push
```powershell
# Ver el commit más reciente del remoto
git log origin/ENHANCE-FE-LE -1

# Ver con detalles
git show origin/ENHANCE-FE-LE
```

### Ver estado de tu rama vs remoto
```powershell
# Ver si estás adelantado o atrasado respecto al remoto
git status

# Ver commits de diferencia
git rev-list --left-right --count origin/ENHANCE-FE-LE...HEAD
```

### Ver todos los branches y sus últimos commits
```powershell
# Ver todas las ramas remotas y sus últimos commits
git branch -r --sort=-committerdate | Select-Object -First 10

# Ver con más detalles
git for-each-ref --sort=-committerdate refs/remotes/origin --format='%(refname:short) - %(committerdate:short) - %(subject)' | Select-Object -First 10
```

## Comando Rápido (Todo en uno)

```powershell
# Ver estado completo de tu rama
Write-Host "=== Tu Rama Actual ===" -ForegroundColor Cyan
$currentBranch = git branch --show-current
Write-Host "Rama: $currentBranch" -ForegroundColor Yellow

Write-Host "`n=== Últimos 5 Commits Remotos ===" -ForegroundColor Cyan
git log origin/$currentBranch --oneline -5

Write-Host "`n=== Commits Locales No Pusheados ===" -ForegroundColor Cyan
$unpushed = git log origin/$currentBranch..HEAD --oneline
if ($unpushed) {
    $unpushed
} else {
    Write-Host "No hay commits sin pushear" -ForegroundColor Green
}

Write-Host "`n=== Commits Remotos No Bajados ===" -ForegroundColor Cyan
$unpulled = git log HEAD..origin/$currentBranch --oneline
if ($unpulled) {
    $unpulled
} else {
    Write-Host "Estás actualizado con el remoto" -ForegroundColor Green
}
```



