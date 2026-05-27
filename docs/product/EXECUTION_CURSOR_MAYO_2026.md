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
| Frente activo | Compliance datos sensibles. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`, `docs/product/BLOCKERS_MAYO_2026.md`, `backend/core/compliance_data_readiness.py`, tests de Compliance readiness y estado real del repositorio. |
| Brecha activa | Revocaciones heredadas de exportaciones sensibles con `revocation_reason` sensible quedan mezcladas como motivo faltante y metadata sensible generica; el readiness debe clasificarlas con codigo especifico sin exponer valores. |
| Motivo de prioridad | Paquete pequeno y local que mejora precision de cierre Compliance sin depender de `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-revocation-reason-readiness`. |
| Rama | `codex/compliance-revocation-reason-readiness`. |
| Estado | Validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Compliance readiness local `classification=parcial`, `ready_for_compliance_data=false` sin fuente autorizada; tests focales e impactados en verde. |
| Estado al cerrar paquete | Focal 3 tests OK; suite impactada Compliance/readiness 82 tests OK; `manage.py check`, `makemigrations --check --dry-run`, gate local Compliance `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 973 tests OK. |
| Bloqueos relacionados | `BLK-010` sigue abierto como condicion de cierre legal-operativo; no bloquea esta preparacion local. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Diagnosticar estado real y seleccionar el siguiente paquete pequeno, local y verificable por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
