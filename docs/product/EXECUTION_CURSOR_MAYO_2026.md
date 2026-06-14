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
| Frente activo | Cerrar `stage6-export-gate`. |
| Fuente exacta | Rama tactica `codex/stage6-export-gate` basada en `main` posterior a `stage6-dossier-review`; verificar SHA real con `git log -1 --oneline`. |
| Brecha activa | `stage6-export-gate`: export/preview local controlado que conecta `AnnualTaxDossier`, source bundle, rule set, matriz DDJJ/F22 y documentos DDJJ/F22 locales sin declarar formato oficial ni presentacion SII. |
| Motivo de prioridad | EDIG muestra que la renta termina en una salida/export revisable antes del upload; LeaseManager necesita una salida propia hasheada y bloqueada por gate, no un salto desde dossier a presentacion. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-export-gate` durante el paquete; tras merge debe quedar solo el root principal esperado, salvo worktrees no relacionados ya existentes. |
| Rama | `codex/stage6-export-gate` durante el paquete; `main` tras merge. |
| Estado | Validado para cierre: `AnnualTaxExport` agrega preview/export local controlado con payload hasheado, refs no sensibles, responsable, conteos DDJJ/F22 y flags obligatorios `official_format=false`, `sii_submission=false`, `final_tax_calculation=false`. API/snapshot/admin redactan refs/payloads; readiness bloquea procesos sin export, con resumen desalineado, invalidos, refs faltantes, revision pendiente o intento de presentacion/formato oficial/calculo final. Pendiente solo PR, CI, merge y limpieza del paquete. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-export-gate` cerrado. Aun faltan formato/certificacion SII vigente, decision tributaria supervisada y autorizacion explicita para cualquier presentacion final. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir metatareas administrativas ya cerradas, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Cerrar PR/CI/merge de `stage6-export-gate`; luego diagnosticar el siguiente frente seguro de Etapa 6/7 sin abrir presentacion SII, EDIG, datos reales ni secretos. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
