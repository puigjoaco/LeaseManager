# Resultado de reemplazo del root - Mayo 2026

## Estado final

`D:/Proyectos/LeaseManager` queda como root limpio activo de LeaseManager. El
root contiene la codebase greenfield, el set canonico y la documentacion viva
necesaria para continuar el desarrollo con Git, ramas y worktrees acotados.

## Identidad Git

- Rama local: `codex/root-clean-integration`.
- Commit base promovido: `9e60d65a7464e06ab158a0a2c36989ff188e4c07`.
- Remote `origin`: `https://github.com/puigjoaco/LeaseManager.git`.
- Upstream: no configurado hasta que el usuario pida push.

## Respaldos

- Savegame completo disponible:
  `D:/Proyectos/LeaseManager-savegame-20260520-082940`.
- Respaldo adicional de remanentes del intento fallido de swap:
  `D:/Proyectos/LeaseManager-failed-swap-contents-20260520-154648`.

No borrar ni reestructurar esos respaldos sin instruccion explicita del usuario.

## Nota de ejecucion

El reemplazo no pudo hacerse mediante renombrado atomico del directorio porque
el root estaba bloqueado por el entorno local. Se ejecuto un swap de contenidos:
se preparo un staging limpio, se respaldaron remanentes del root bloqueado y se
movio el contenido limpio validado al path principal.

## Validacion post-swap

Fecha: 2026-05-20.

- `git status -sb`: limpio, con solo artefactos ignorados de entorno local.
- `npm ci`: OK en `frontend/`.
- `npm audit --audit-level=moderate`: OK, cero vulnerabilidades reportadas.
- `npm run build`: OK en `frontend/`.
- `.venv` recreado en `backend/` y dependencias instaladas.
- `manage.py check`: OK.
- PostgreSQL y Redis locales levantados con `infra/docker-compose.yml` y
  reportados como healthy.
- `manage.py migrate --noinput`: OK contra PostgreSQL local.
- `manage.py test --noinput -v 1`: OK, 263/263 tests.

No se hizo push, deploy, migracion productiva, backfill real ni copia de
secretos desde el root historico.
