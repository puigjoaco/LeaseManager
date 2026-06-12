# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion convierta contexto auxiliar en tarea
nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Etapa 2 / Canales - normalizacion antes de `full_clean()`. |
| Fuente exacta | `main` limpio en `2007ca64`; worktree tactico `D:/Proyectos/LeaseManager-stage2-channels-full-clean-normalization`; rama `codex/stage2-channels-full-clean-normalization`; rescue pausado fuera de alcance. |
| Brecha activa | `CanalMensajeria`, `ConfiguracionNotificacionContrato`, `MensajeSaliente` y `NotificacionCobranzaProgramada` normalizaban refs/textos operativos en `clean()`/`save()`, pero no antes de que `full_clean()` ejecutara validadores de campo. |
| Motivo de prioridad | Paquete local, pequeno y verificable; alinea Canales con el hardening ya aplicado en Conciliacion, Contabilidad y Documentos sin tocar proveedores, secretos ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-channels-full-clean-normalization`. |
| Rama | `codex/stage2-channels-full-clean-normalization`. |
| Estado | Implementacion y validacion local completas; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Gate local Etapa 2 debe quedar `classification=parcial`, `ready_for_stage2_cobranza=false`, sin cierre evidencial falso. |
| Estado al cerrar paquete | Validacion local ejecutada: focal Canales 1 test, suite impactada Canales/readiness 180 tests, `manage.py check`, migraciones dry-run, gate Etapa 2 local `classification=parcial`, `npm ci`, `npm run build`, `npm run lint` y acceptance local 1298 tests. Confirmar PR/CI remoto y merge antes de considerar integrado. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; si solo aparece el rescue pausado, continuar con el siguiente paquete pequeno, local, verificable y cerrable sin tocar esos archivos. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
