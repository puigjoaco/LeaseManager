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
| Frente activo | Etapa 2 / Cobranza admin closed surface. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `CodigoCobroResidualAdmin` y `EstadoCuentaArrendatarioAdmin` aun permiten alta manual desde Django admin, aunque sus registros deben nacer de servicios/generacion/rebuild para no saltar reglas de CobranzaActiva. |
| Motivo de prioridad | Etapa 2 mantiene cerrada la superficie administrativa para cobros operativos; esta brecha es local, pequena y verificable sin proveedores, secretos ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-cobranza-admin-closed-surface`. |
| Rama | `codex/stage2-cobranza-admin-closed-surface`. |
| Estado | Abierto en implementacion. |
| Gate esperado | Tests focales de admin Cobranza, suite impactada Cobranza/Stage 2, gate local Etapa 2, acceptance local, CI remoto acceptance e higiene. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, seleccionar el proximo paquete pequeno, seguro y verificable desde `TRACEABILITY_MATRIX_MAYO_2026.md`, stage cards y orden de construccion. |
| Siguiente accion | Cerrar alta manual de residuales/estados de cuenta en admin, cubrir con tests, actualizar stage card/trazabilidad/evidencia y validar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
