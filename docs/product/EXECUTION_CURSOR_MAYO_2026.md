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
| Frente activo | `codex/stage6-controlled-presentation-package`. |
| Fuente exacta | `main` en `006d9d78`, despues del merge confirmado de PR #931 `codex/stage6-presentation-artifact-coverage`. |
| Brecha activa | Los artefactos F22/DDJJ/export ya se verifican y cubren exactamente la matriz, pero faltaba un paquete local de entrega controlada que solo exista despues de un bundle aprobado y que deje refs de handoff sin abrir SII real. |
| Motivo de prioridad | Para pasar de revision comparativa a una entrega usable por responsable tributario, el sistema debe sellar una raiz reproducible con paquete anual, F22, DDJJ ASCII/ZIP, bundle aprobado y manifest de handoff, sin mezclar corridas ni sugerir presentacion automatica. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-controlled-presentation-package`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-controlled-presentation-package`. |
| Estado | Paquete en ejecucion: agregar `materialize_annual_tax_controlled_presentation_package`, builders/verificadores del manifest `annual-tax-controlled-presentation-package`, cobertura de checklist no aprobado, salida completa, salida no vacia y salida versionada, registrar evidencia y cerrar por PR/CI/merge. |
| Gate esperado | Este paquete usa solo fixtures, SQLite efimero y manifests locales bajo `local-evidence`. No lee `.env`, DB real, documentos reales, correos, adjuntos, EDIG ejecutable, banco ni SII autenticado; no declara contabilidad final, calculo tributario final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente contable seguro desde repo limpio. |
| Bloqueos relacionados | Carga productiva real, documentos completos, manifest real redactado/autorizado, formato/certificacion F22/DDJJ aplicable, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita y evidencia no sensible. AT2025 conserva brecha `f22_record_format_2025` hasta evidencia oficial/experta vigente. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. Un paquete preparado solo habilita revision responsable; nunca contabilidad autonoma ni presentacion automatica. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, ampliar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el siguiente frente seguro de contabilidad/renta. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
