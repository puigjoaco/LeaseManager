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
| Frente activo | Boundary contable/tributario asistido: alinear PRD, arquitectura, gates y stage cards para que LeaseManager prepare paquetes trazables, no decisiones autonomas de renta/contabilidad. |
| Fuente exacta | `main` limpio `2eed3291` tras mergear PR #803. Rescue queda pausado fuera de alcance. |
| Brecha activa | Lenguaje documental aun podia leerse como contabilidad/renta final automatizada. Debe quedar explicito que el core mecaniza datos, reglas, evidencias, asientos y dossiers, mientras la aprobacion/presentacion final exige responsable, gate y validacion experta/oficial. |
| Motivo de prioridad | Evitar que el siguiente avance endurezca automatizacion tributaria o contable mas alla del boundary real del v1; mantener avance ordenado y trazable hacia cierre sin crear decisiones autonomas inseguras. |
| Worktree | `D:/Proyectos/LeaseManager-accounting-tax-boundary`. |
| Rama | `codex/accounting-tax-boundary`. |
| Estado | En desarrollo documental, sin tocar codigo operativo ni datos reales. |
| Gate esperado | Revision textual de PRD, matriz de gates, arquitectura y stage cards 4/5/6/7; `git diff --check`, higiene repo y PR/CI antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | No hay bloqueo externo para este paquete. Cierres reales de Etapas 5, 6 y 7 siguen condicionados a fuentes autorizadas, evidencia no sensible, responsables y gates aplicables. |
| Politica de reanudacion | No reabrir PR #803 ni redactar goal. Continuar este paquete hasta PR/CI/merge/limpieza; luego seleccionar el siguiente frente seguro desde el repo. |
| Siguiente accion | Terminar ajuste documental, validar diff/higiene, abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
