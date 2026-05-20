# Ordenamiento profesional del root - Mayo 2026

## Objetivo

Convertir LeaseManager en un repositorio limpio, integrable y profesional, con
desarrollo gobernado por Git, ramas y worktrees. El root sucio actual se conserva
como savegame/fuente historica; el root final debe contener solo producto,
codigo, documentacion viva, gates reproducibles y evidencia no sensible.

## Estado verificado

- `D:/Proyectos/LeaseManager` es ahora el root limpio activo con la codebase
  greenfield Django/DRF/PostgreSQL/Celery/Redis y React/Vite.
- El root historico Next/Supabase quedo preservado como savegame/fuente de
  rescate. No debe recibir desarrollo nuevo.
- `D:/Proyectos/LeaseManager-clean-origin` es clon limpio de `origin/main` en
  GitHub, commit `c58cb44806f0a1cf225bac20e621cc5685d95a11`.
- `D:/Proyectos/LeaseManager-lab-root-clean` es el worktree de laboratorio para
  integrar y validar antes de reemplazar el root principal.
- `D:/Proyectos/LeaseManager/Produccion 1.0` es un repo anidado con rama
  `codex/review-findings-fixes`; contiene commits utiles que deben integrarse o
  descartarse por evidencia, no copiarse a ciegas.

## Decision operativa

El candidato limpio parte desde `origin/main`, no desde el root sucio. El root
sucio no recibe desarrollo nuevo salvo rescate puntual. Toda migracion se hace
por diff, clasificacion y validacion.

## Fuentes que se pueden rescatar

- Set vigente: `01_Set_Vigente/`, `02_ADR_Activos/`, `03_Ejecucion_Tecnica/` y
  `08_Auditoria_Stack/`, si siguen alineados al estado real.
- Candidatos generados en el root historico: `docs/product/` y documentos de
  `docs/production-readiness/`, solo despues de depurar rutas, herencia y
  contradicciones.
- Codigo del root historico solo si una auditoria demuestra que corresponde al
  producto final y no contradice el stack vigente.
- Contextos Excel/negocio solo como reglas verificables; no se copian secretos,
  snapshots reales ni evidencia sensible.

## Herencia que queda fuera del root limpio

- `.taskmaster/`, `.claude/`, comandos legacy, docs de herramientas,
  repositorios anidados completos, `.next/`, `node_modules/`, capturas,
  logs, caches, temporales, credenciales, certificados reales, snapshots reales
  y artefactos locales.
- Los PRD crudos e intermedios quedan como trazabilidad historica salvo que una
  auditoria detecte una regla faltante que deba elevarse al canon vigente.

## Fases de ejecucion

1. Congelar: confirmar savegame, estado Git, remotos, worktrees y ramas.
2. Base limpia: usar `LeaseManager-clean-origin` como espejo de GitHub y
   `LeaseManager-lab-root-clean` como rama de integracion.
3. Reconciliar codigo greenfield: comparar `origin/main` con
   `codex/review-findings-fixes`, integrar commits utiles y resolver los dos
   commits de `main` que esa rama no tiene.
4. Migrar documentacion viva: traer solo PRD/anexos/plan/auditorias depuradas y
   adaptar referencias para que no apunten al root historico como operativo.
5. Migrar controles: incorporar scripts/gates necesarios si aplican al stack
   vigente y si no dependen de rutas legacy, secretos o mocks.
6. Validar: ejecutar checks backend, migraciones locales controladas, build
   frontend, smoke local, auditorias documentales y revision de secretos.
7. Preparar swap: generar inventario final, confirmar que no hay trabajo sin
   respaldo, cerrar procesos locales y documentar rollback.
8. Reemplazar root: renombrar el root sucio a savegame definitivo y mover el
   limpio validado a `D:/Proyectos/LeaseManager`.
9. Post-swap: revalidar rutas, Git, worktrees, build, tests y docs desde el
   nuevo root principal.

## Gates minimos antes del swap

- `git status -sb` limpio o con cambios intencionales listos para commit.
- Backend: `python manage.py check` y pruebas criticas del alcance.
- Frontend: `npm run build`.
- Infra local documentada sin credenciales reales.
- Auditoria de secretos sin hallazgos versionados.
- Auditoria documental sin referencias operativas a TaskMaster/Claude ni a
  rutas historicas como fuente viva.
- Lista de bloqueadores reales, si existen, sin ocultarlos como avance.

## Validacion inicial del laboratorio

Fecha: 2026-05-20.

- Worktree creado: `D:/Proyectos/LeaseManager-lab-root-clean`.
- Rama: `codex/root-clean-integration`, basada en `origin/main`.
- Frontend: `npm ci`, `npm audit fix`, `npm audit --audit-level=moderate` y
  `npm run build` ejecutados correctamente; auditoria npm queda en cero
  vulnerabilidades conocidas.
- Backend: `.venv` local creado, dependencias instaladas y `manage.py check`
  ejecutado correctamente.
- Backend tests con entorno local aislado: `manage.py test --noinput` pasa con
  overrides `DJANGO_DEBUG=true`,
  `DATABASE_URL=sqlite:///test-codex-local-gate.db` y
  `DJANGO_CACHE_URL=locmem://test-cache`: 263/263 OK.
- Infra real local: Docker Desktop iniciado, PostgreSQL y Redis levantados con
  `infra/docker-compose.yml`, ambos en estado `healthy`.
- Backend con PostgreSQL/Redis locales: `manage.py migrate --noinput` OK y
  `manage.py test --noinput -v 1` OK, 263/263 tests.
- Correcciones PostgreSQL aplicadas: fixture de `reporting` ajustado a
  `codigo_propiedad.max_length=16` y migracion `cobranza.0005` marcada
  `atomic = False` para permitir backfill seguido de constraints en PostgreSQL.
- Higiene Git: se detectaron 49 archivos `.pyc` versionados. Quedan marcados
  para eliminacion porque `.gitignore` ya bloquea `__pycache__/` y `*.pyc`.

## Resultado del reemplazo de root

Fecha: 2026-05-20.

- Root limpio activo: `D:/Proyectos/LeaseManager`.
- Rama local: `codex/root-clean-integration`.
- Commit promovido: `9e60d65a7464e06ab158a0a2c36989ff188e4c07`.
- Remote `origin`: `https://github.com/puigjoaco/LeaseManager.git`.
- Upstream: sin configurar hasta que el usuario pida push.
- Savegame completo disponible:
  `D:/Proyectos/LeaseManager-savegame-20260520-082940`.
- Respaldo adicional de remanentes del intento fallido de swap:
  `D:/Proyectos/LeaseManager-failed-swap-contents-20260520-154648`.
- El reemplazo se ejecuto como swap de contenidos porque el directorio root
  estaba bloqueado por el entorno local y no podia renombrarse de forma atomica.
- No se hizo push, deploy, migracion productiva ni copia de secretos.

Validacion post-swap desde el nuevo root:

- `git status -sb`: limpio, con solo artefactos ignorados de entorno local.
- Frontend: `npm ci`, `npm audit --audit-level=moderate` y `npm run build` OK.
- Backend: `.venv` recreado, dependencias instaladas, `manage.py check` OK.
- Infra local: PostgreSQL y Redis via `infra/docker-compose.yml` healthy.
- Backend con PostgreSQL/Redis locales: `manage.py migrate --noinput` OK y
  `manage.py test --noinput -v 1` OK, 263/263 tests.

## Definition of Done del ordenamiento

El ordenamiento termina cuando `D:/Proyectos/LeaseManager` vuelve a ser el root
limpio, el root sucio queda preservado como savegame, Git representa el estado
real del proyecto, los worktrees salen de una base limpia, la documentacion
rectora esta en rutas activas, los gates son ejecutables y no queda herencia
operativa contaminando el flujo de desarrollo.
