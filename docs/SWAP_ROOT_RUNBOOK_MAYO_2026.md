# Runbook de reemplazo del root - Mayo 2026

## Objetivo

Reemplazar `D:/Proyectos/LeaseManager` por una base limpia validada, dejando el
root sucio como savegame recuperable. El reemplazo no debe destruir historia,
secretos locales, evidencia ni artefactos que aun puedan servir para auditoria.

## Criterio tecnico

El root final no debe quedar como worktree dependiente de
`D:/Proyectos/LeaseManager-clean-origin`. Debe quedar como clon Git normal o
como repositorio promovido con `.git` propio. Esto evita que borrar una carpeta
auxiliar rompa el proyecto principal.

## Preflight obligatorio

1. Confirmar que `D:/Proyectos/LeaseManager-lab-root-clean` contiene la rama
   validada.
2. Confirmar `git status -sb` limpio en el laboratorio.
3. Confirmar que no hay servidores, editores o terminales usando el root sucio.
4. Confirmar respaldo existente y crear savegame final si corresponde.
5. Ejecutar gates minimos:
   - frontend: `npm audit --audit-level=moderate` y `npm run build`;
   - backend: `manage.py check`;
   - backend tests con entorno local controlado;
   - infra PostgreSQL/Redis con Docker si el daemon esta disponible.
6. Confirmar que no se copiaran `.env`, certificados reales, `node_modules`,
   `.venv`, `dist`, `__pycache__`, caches, capturas ni repos anidados.

## Opcion recomendada: clon limpio independiente

Usar esta opcion cuando la rama de laboratorio ya esta lista y se quiere que el
nuevo `D:/Proyectos/LeaseManager` tenga `.git` propio.

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$oldRoot = "D:/Proyectos/LeaseManager"
$backup = "D:/Proyectos/LeaseManager-savegame-final-$timestamp"
$source = "D:/Proyectos/LeaseManager-clean-origin"
$newRoot = "D:/Proyectos/LeaseManager"

git -C "D:/Proyectos/LeaseManager-lab-root-clean" status -sb
git -C "D:/Proyectos/LeaseManager-lab-root-clean" rev-parse --abbrev-ref HEAD

Move-Item -LiteralPath $oldRoot -Destination $backup
git clone --branch codex/root-clean-integration $source $newRoot
```

Despues del clon:

```powershell
git -C "D:/Proyectos/LeaseManager" status -sb
git -C "D:/Proyectos/LeaseManager" log --oneline -5
cd "D:/Proyectos/LeaseManager/frontend"
npm ci
npm audit --audit-level=moderate
npm run build
cd "D:/Proyectos/LeaseManager/backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG='true'
$env:DATABASE_URL='sqlite:///test-codex-local-gate.db'
$env:DJANGO_CACHE_URL='locmem://test-cache'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --noinput -v 1
```

## Rollback

Si el nuevo root falla preflight o gates post-swap:

```powershell
Rename-Item -LiteralPath "D:/Proyectos/LeaseManager" -NewName "LeaseManager-failed-swap-$timestamp"
Rename-Item -LiteralPath $backup -NewName "LeaseManager"
```

Luego registrar:

- comando que fallo;
- salida relevante;
- si el fallo es codigo, entorno, dependencia externa o decision pendiente;
- proxima accion.

## Prohibiciones

- No borrar el savegame final hasta que el usuario lo acepte explicitamente.
- No hacer deploy durante el swap.
- No ejecutar migraciones reales ni backfills reales.
- No copiar secretos desde el root historico al root limpio.
- No declarar listo si Docker/PostgreSQL/Redis real quedo sin validar y esa
  validacion era requisito del alcance.
