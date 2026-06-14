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
| Frente activo | Mapeo EDIG AT2026 para motor de renta anual LeaseManager. |
| Fuente exacta | Solicitud del usuario: implementar el plan de mapeo EDIG AT2026 -> LeaseManager para entender contabilidad, RLI/CPT/RAI/SAC, DDJJ, F22, validaciones y upload/export SII sin copiar codigo propietario ni versionar EDIG. |
| Brecha activa | Etapa 6 tenia boundary asistido, pero faltaba una matriz implementable que explicara como unir contabilidad y renta mediante capa tributaria intermedia y como investigar EDIG con sandbox seguro. |
| Motivo de prioridad | Reduce ambiguedad estrategica de Renta Anual y evita dos errores: F22 directo desde asientos o IA autonoma sin regla/gate. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-edig-tax-mapping`. |
| Rama | `codex/edig-tax-mapping`. |
| Estado | Paquete documental/operativo en curso: matriz EDIG->LeaseManager, runbook de sandbox, script de inventario read-only y proteccion Git de EDIG. No ejecutar EDIG en el root activo. |
| Gate esperado | Validar que EDIG sigue ignorado/no trackeado, script parsea y ejecuta inventario estatico sin ejecutar binarios, salida queda en `local-evidence/`, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Dejar Etapa 6 alineada con normalizador anual RLI/CPT/RAI/SAC/DDJJ/F22 versionado por ano tributario, con EDIG como referencia no normativa y sin cierre de gate SII. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No usar PDFs tributarios reales del worktree externo ni ejecutar EDIG fuera de sandbox. Si el paquete queda interrumpido, continuar en `codex/edig-tax-mapping` y no reabrir conversaciones de goal. |
| Siguiente accion | Ejecutar validaciones locales del paquete, abrir PR y esperar CI si aplica. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
