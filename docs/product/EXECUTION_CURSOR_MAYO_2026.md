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
| Frente activo | Cerrar `stage6-dossier-review` y, tras merge/limpieza, continuar con `stage6-export-gate`. |
| Fuente exacta | Rama tactica `codex/stage6-dossier-review` basada en `main` posterior a `stage6-ddjj-f22-artifact-matrix`; verificar SHA real con `git log -1 --oneline`. |
| Brecha activa | `stage6-dossier-review`: dossier anual revisable que consolida source bundle, hechos mensuales, RLI/CPT, registros empresariales, bienes raices y matriz DDJJ/F22 con responsable. |
| Motivo de prioridad | La capa intermedia anual ya enlaza fuentes, workbooks, registros, bienes raices y matriz DDJJ/F22; corresponde producir el dossier revisable antes de cualquier export/presentacion SII. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-dossier-review` durante el paquete; tras merge debe quedar solo el root principal esperado, salvo worktrees no relacionados ya existentes. |
| Rama | `codex/stage6-dossier-review` durante el paquete; `main` tras merge. |
| Estado | `stage6-dossier-review` agrega `AnnualTaxDossier`: consolida source bundle, hechos mensuales, RLI/CPT, registros empresariales, bienes raices y matriz DDJJ/F22 en resumen hasheado con responsable y refs no sensibles. API/snapshot/admin redactan refs/payloads; readiness bloquea procesos sin dossier, con resumen desalineado, invalidos, sin responsable/dossier ref, con warnings o revision pendiente. Mantiene `final_tax_calculation=false` y `sii_submission=false`. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, validacion fiscal/oficial, dossier revisable aprobado por responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-dossier-review` cerrado. Aun faltan export/preview controlado, formato/certificacion SII vigente y decision tributaria supervisada. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir metatareas administrativas ya cerradas, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Validar y cerrar `stage6-dossier-review`; luego diagnosticar `stage6-export-gate` contra PRD/blueprint sin abrir presentacion SII ni datos reales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
