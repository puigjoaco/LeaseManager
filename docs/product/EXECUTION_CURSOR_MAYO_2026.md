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
  explicita en este cursor o descartar con instruccion segura antes de abrir un frente
  distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.
- Si este cursor nombra una rama/worktree ya cerrados y `main` contiene el
  merge correspondiente, no recrear el paquete anterior: tratarlo como cerrado,
  corregir este cursor y continuar con el siguiente frente seguro.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | `codex/reporting-review-company-ref-display`. |
| Fuente exacta | `main` en `e9becb27`, despues del merge confirmado de PR #928 `codex/company-review-manifest-company-ref`. |
| Brecha activa | El core/API ya bloquea manifiestos bancarios/leasing de otra empresa, pero el backoffice de Reporting aun no muestra al revisor `expected_company_ref` y `bank_support_company_ref`; el bloqueo queda visible solo como issue tecnico. |
| Motivo de prioridad | La revision responsable debe poder distinguir en pantalla si el paquete esta pendiente por cobertura documental, avance contable o manifiesto cruzado de empresa, sin abrir adjuntos, banco, SII ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-reporting-review-company-ref-display`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/reporting-review-company-ref-display`. |
| Estado | Paquete en ejecucion: tipar y mostrar en backoffice la referencia canonica esperada y la referencia del manifiesto, y ajustar el manifiesto demo a `company-1` como ejemplo no sensible. |
| Gate esperado | Este paquete solo cambia UI/tipos/documentacion sobre datos ya redactados que entrega la API. No lee `.env`, DB real, documentos reales, correos, adjuntos, EDIG ejecutable, banco ni SII autenticado; no declara contabilidad final, calculo tributario final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Carga productiva real, documentos completos, manifest real redactado/autorizado, formato/certificacion F22/DDJJ aplicable, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. El panel solo muestra frontera y referencias redactadas para revision responsable; nunca contabilidad autonoma ni presentacion automatica. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, registrar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el siguiente frente seguro. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
