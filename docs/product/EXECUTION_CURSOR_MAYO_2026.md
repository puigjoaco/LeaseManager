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
| Frente activo | Etapa 1 - Patrimonio: ventana efectiva de representaciones de comunidad. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Patrimonio`; `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md`; `backend/patrimonio/models.py`; `backend/patrimonio/serializers.py`; `backend/core/stage1_matrix_audit.py`; tests de Patrimonio/Etapa 1. |
| Brecha activa | Las representaciones de comunidad con `vigente_desde` futuro pueden contarse como vigentes si `activo=True`, lo que permite activar comunidades o bloquear desactivaciones antes de la vigencia real. |
| Motivo de prioridad | La trazabilidad exige participaciones y representaciones actualmente vigentes; es un paquete local, pequeno y verificable sin secretos ni fuentes externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-representation-effective-window`. |
| Rama | `codex/stage1-representation-effective-window`. |
| Estado | En implementacion. `main` queda limpio en `D:/Proyectos/LeaseManager`. |
| Gate esperado | Etapa 1 local diagnostica parcial/no evidencial; no cierra Etapa 1 sin `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Cierre real de Etapa 1 sigue dependiendo de fuente autorizada y evidencia suficiente; no bloquea este hardening local. |
| Politica de reanudacion | Retomar este worktree hasta cerrar, pausar explicitamente en este cursor o limpiar con instruccion segura. |
| Siguiente accion | Ajustar dominio/API/auditor para usar `vigente_desde <= hoy` en representaciones vigentes, agregar pruebas focales y ejecutar validacion proporcional. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
