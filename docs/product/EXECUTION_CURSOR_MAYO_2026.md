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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 0 - Compliance datos sensibles, formato SHA-256 real para `payload_hash` de exportaciones sensibles. |
| Fuente exacta | PR #227 `Guard Compliance export hash format`; commit `4b3b38a`; merge `16d9c23`; `backend/compliance/models.py`; `backend/core/compliance_data_readiness.py`; tests de Compliance/readiness; trazabilidad y evidencia actualizadas. |
| Brecha activa | Cerrada localmente: `ExportacionSensible.full_clean` rechaza `payload_hash` no hexadecimal aunque tenga 64 caracteres y readiness clasifica snapshots heredados con `compliance.export_payload_hash_invalid`. |
| Motivo de prioridad | Paquete local, pequeno y verificable completado sin secretos, `.env`, DB historica, datos reales ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal `D:/Proyectos/LeaseManager`. |
| Rama | `main`, sincronizada con `origin/main`. |
| Estado | PR #227 integrado con CI remoto verde; worktree tactico y ramas local/remota eliminados. |
| Gate esperado | Compliance local diagnostica parcial/no evidencial; no cierra `Compliance.DatosPersonalesChile2026` sin fuente autorizada, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa. |
| Estado al cerrar paquete | Preparacion local de Compliance reforzada; cierre real de Compliance sigue pendiente de fuente autorizada, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa. |
| Bloqueos relacionados | Fuente/evidencia legal-operativa autorizada sigue siendo condicion de cierre, no freno para elegir otro paquete local seguro. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, diagnosticar el siguiente paquete pequeno, trazable y local desde la matriz/stage cards. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; elegir el siguiente frente seguro por trazabilidad y abrir worktree `codex/...` solo si requiere cambios no triviales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
