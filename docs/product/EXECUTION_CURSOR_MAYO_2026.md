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
| Frente activo | Etapa 0 - Compliance datos sensibles: formato SHA-256 real para `payload_hash` de exportaciones sensibles. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`; `backend/compliance/models.py`; `backend/core/compliance_data_readiness.py`; tests de Compliance/readiness. |
| Brecha activa | El modelo/readiness exigen hash de 64 caracteres, pero no verifican que `payload_hash` sea hexadecimal SHA-256; un snapshot heredado podria conservar un valor de 64 caracteres no hex. |
| Motivo de prioridad | Primer frente parcial por orden, hardening local pequeno y verificable sin secretos, `.env`, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-export-hash-format`. |
| Rama | `codex/compliance-export-hash-format`. |
| Estado | En implementacion. `main` queda limpio en `D:/Proyectos/LeaseManager`. |
| Gate esperado | Compliance local diagnostica parcial/no evidencial; no cierra `Compliance.DatosPersonalesChile2026` sin fuente autorizada, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Cierre real de Compliance sigue dependiendo de refs y fuente autorizada; no bloquea este hardening local. |
| Politica de reanudacion | Retomar este worktree hasta cerrar, pausar explicitamente en este cursor o limpiar con instruccion segura. |
| Siguiente accion | Validar `payload_hash` hexadecimal en dominio/readiness, agregar pruebas focales y documentar evidencia/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
