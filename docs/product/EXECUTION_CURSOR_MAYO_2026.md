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
| Frente activo | Etapa 2 - CobranzaActiva. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `CodigoCobroResidual` conserva superficie de mutacion generica despues de creado desde API detail/admin, permitiendo alterar saldo, estado o target sin flujo bancario exacto ni resolucion auditada especifica. |
| Motivo de prioridad | El PRD exige deuda residual con referencia propia y trazabilidad; el codigo residual ya se genera con referencia canonica, pero debe quedar inmutable desde superficies genericas despues de creado. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-residual-code-readonly`. |
| Rama | `codex/stage2-residual-code-readonly`. |
| Estado | Paquete tactico abierto. Ultimo paquete cerrado: PR #507 `Make account state admin fields read-only`, merge `646ede81a240f94cb02671376d44de6d75633c38`. |
| Gate esperado | Tests focales de Cobranza para API/admin de codigos residuales, suite impactada Cobranza + readiness Etapa 2, `manage.py check`, migraciones dry-run, gate local Etapa 2, frontend build/lint, acceptance local, higiene y `git diff --check`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, abrir el siguiente paquete pequeno, seguro y verificable segun trazabilidad, stage cards y orden de construccion. |
| Siguiente accion | Bloquear mutaciones genericas posteriores a la creacion de `CodigoCobroResidual`, dejar admin en solo lectura para registros existentes y validar/documentar el paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
