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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 5 - Documentos PDF, responsable obligatorio en documento emitido. |
| Fuente exacta | PR #233 `Guard Stage 5 document responsible user`; commit `4206a8d`; merge `f599c6a`; `backend/documentos/models.py`; `backend/documentos/serializers.py`; `backend/documentos/tests.py`; stage card, trazabilidad y evidencia actualizadas. |
| Brecha activa | Cerrada localmente: `DocumentoEmitido.clean()` rechaza documentos sin `usuario`, la API valida create con el usuario autenticado y readiness conserva `documents.user_missing` para snapshots heredados. |
| Motivo de prioridad | Brecha local trazable de Documentos cerrada sin usar storage real, `.env`, datos reales ni integraciones externas. |
| Worktree | Ninguno. |
| Rama | `main` sincronizada con `origin/main` tras PR #233. |
| Estado | PR #233 integrado con CI remoto en verde; paquete tactico limpiado. |
| Gate esperado | Etapa 5 Documentos local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, politica final, prueba PDF controlada y responsable. |
| Estado al cerrar paquete | Cerrado e integrado en `main` con validacion local y CI remoto. |
| Bloqueos relacionados | Politica final, prueba PDF controlada y fuente autorizada siguen siendo condicion de cierre, no freno para este hardening local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente frente util desde stage cards, matriz de trazabilidad y PRD, abrir worktree `codex/...` si corresponde y avanzar con validaciones proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
