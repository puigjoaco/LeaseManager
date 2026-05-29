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
| Frente activo | CobranzaActiva / admin operativo. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, `CODEX_OPERATING_PROTOCOL_MAYO_2026.md`, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Los admins operativos de Cobranza bloqueaban alta y borrado manual, pero aun podian abrir flujo de cambio manual desde Django admin. |
| Motivo de prioridad | Etapa 2 exige que UF, ajustes, pagos, WebPay, garantias, repactaciones, residuales y estados de cuenta pasen por API, servicios, reconstruccion, conciliacion o resolucion formal auditada; no por mutacion manual de admin. |
| Worktree | `D:/Proyectos/LeaseManager-cobranza-admin-change-guard`. |
| Rama | `codex/cobranza-admin-change-guard`. |
| Estado | Paquete tactico abierto para bloquear edicion manual de admins operativos de Cobranza, conservando inspeccion redactada y sin conectar WebPay real. |
| Gate esperado | Focal Cobranza admin; suite Cobranza/readiness Etapa 2; `manage.py check`; migraciones dry-run; gate local Etapa 2 parcial; frontend build/lint; acceptance local; higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; CobranzaActiva/Etapa 2 sigue parcial para cierre real por datos Etapa 1, fuente autorizada y pruebas externas/controladas de Email/WebPay, pero esta preparacion local no depende de datos reales ni integraciones externas. |
| Politica de reanudacion | Si no existe worktree tactico sucio, abrir el siguiente paquete pequeno, seguro y verificable segun trazabilidad, stage cards y orden de construccion. |
| Siguiente accion | Implementar guard de `has_change_permission`, validar y cerrar PR. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
