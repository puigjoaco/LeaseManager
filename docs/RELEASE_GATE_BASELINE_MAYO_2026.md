# Release gate baseline - Mayo 2026

## Objetivo

Cerrar la primera limpieza tecnica posterior al merge del root limpio a `main`.
El objetivo no es declarar produccion, sino dejar el repositorio activo mas
cerca de un baseline profesional: producto vivo en Git, herencia en savegame,
artefactos generados fuera del flujo diario y gates reproducibles.

## Estado del root

- Root activo: `D:/Proyectos/LeaseManager`.
- Rama diaria: `main`.
- Savegames externos conservados:
  - `D:/Proyectos/LeaseManager-savegame-20260520-082940`
  - `D:/Proyectos/LeaseManager-failed-swap-contents-20260520-154648`
- No se ejecuta deploy, backfill productivo ni migracion real desde este frente.

## Limpieza aplicada

Se retiraron del repo activo artefactos que pertenecen a evidencia historica o
salidas locales, no al producto vivo:

- `backend/bundle-inspect-final.db`
- `backend/bundle-inspect.db`
- `backend/test-codex.db`
- capturas `.png` historicas bajo `migration/bundles/`
- JSON historicos de migracion/staging bajo `migration/bundles/`
- paquete `HANDOFF/` historico y handoffs greenfield antiguos que apuntaban al
  root anidado `Produccion 1.0`

Esos archivos siguen recuperables desde el savegame y desde historial Git, pero
no deben viajar como parte del root activo.

## Reglas de no regresion

`.gitignore` queda reforzado para bloquear:

- bases SQLite/DB locales en `backend/`;
- bases de test locales;
- JSON generados bajo `migration/bundles/`;
- capturas generadas bajo `migration/bundles/`;
- screenshots locales;
- handoffs historicos del antiguo root anidado.

El asset `frontend/src/assets/hero.png` se conserva porque es parte de la app.

## Gates existentes

- `.github/workflows/release-gate.yml` ejecuta el gate deterministico en PR y
  push a `main`: backend acceptance, `manage.py check` y frontend build.
- El smoke publico contra URLs externas queda separado como `workflow_dispatch`
  manual con `run_public_smoke=true`.
- `scripts/run-acceptance-workflows.ps1` cubre backend acceptance, `manage.py
  check`, frontend build y smoke publico opcional/manual.

## Validacion local

- `git diff --cached --check`: OK.
- Auditoria de artefactos rastreados: sin `.db`, SQLite, screenshots de
  `migration/bundles/`, `HANDOFF/` ni handoffs greenfield antiguos.
- `D:/Proyectos/LeaseManager/backend/.venv/Scripts/python.exe manage.py check`
  ejecutado desde el worktree: OK.
- `npm run build` ejecutado en frontend con `node_modules` enlazado localmente
  desde el root limpio principal: OK.
- PR #5: gate remoto de PR OK.
- Push posterior a `main`: backend acceptance, `manage.py check` y frontend
  build OK; fallo solo el smoke publico externo. Por eso el smoke publico queda
  separado del gate deterministico hasta tener ambiente externo aceptado.
- `./scripts/run-acceptance-workflows.ps1 -SkipSmoke`: OK despues de separar
  CI deterministico y smoke publico manual.

## Bloqueos que siguen vivos

- CI remoto deterministico quedo verde en `main` despues del PR #6.
- El smoke publico depende de URLs externas y debe ejecutarse manualmente como
  gate externo, no como requisito automatico de cada push mientras no exista
  ambiente publico aceptado.
- Integraciones reales Banco, UF automatica, Email/WhatsApp, SII, Railway y Vercel siguen bajo gates externos.
- No hay cutover productivo sin datos reales/controlados, backup, rollback y aprobacion.
- Falta cerrar Etapa 1 con datos reales o snapshot controlado.

## Proximo paso

Despues de este baseline y de la promocion del PRD Mayo 2026, mantener `main`
limpio y continuar mediante worktrees por frente. El proximo cierre profesional
es avanzar Etapa 1 con datos reales o controlados y mantener integraciones
externas bajo gates separados.
