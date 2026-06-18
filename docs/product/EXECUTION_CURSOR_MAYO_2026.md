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
| Frente activo | `codex/stage6-presentation-review-bundle`. |
| Fuente exacta | `main` en `725e65cd`, despues del merge confirmado de PR #923 `codex/stage6-ddjj-candidate-materializers`. |
| Brecha activa | F22, DDJJ ASCII/ZIP y paquete `AnnualTaxExport` ya pueden materializarse localmente por separado, pero falta una superficie operativa unica que arme un bundle verificable de revision previa a presentacion desde artefactos ya materializados, sin exponer identificadores ni declarar envio SII. |
| Motivo de prioridad | Etapa 6 necesita unir evidencia local revisable en un paquete de presentacion controlada: export package, candidato F22, candidato DDJJ ASCII/ZIP, decision actual del checklist, hashes y boundary externo. Eso permite revision responsable sin convertir LeaseManager en motor autonomo de renta o presentacion. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-presentation-review-bundle`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-presentation-review-bundle`. |
| Estado | Paquete en ejecucion: agrega verificador/builder de bundle de revision de presentacion, comando `materialize_annual_tax_presentation_review_bundle`, cobertura focal y documentacion de boundary. |
| Gate esperado | Este paquete no declara formato oficial, certificacion, upload, presentacion SII, autorizacion de envio ni calculo tributario final. Solo consolida evidencia candidata local ya verificada para revision responsable. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | La decision tributaria final, formato/certificacion F22/DDJJ, codigo autorizado por SII, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita, formato/certificacion vigente aplicable y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. La aprobacion para presentacion solo puede existir como decision y evidencia trazables no sensibles; nunca como salida automatica del motor local. |
| Siguiente accion | Completar validaciones proporcionales, registrar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. Si `main` ya contiene el merge de este frente, no reabrirlo: tomar el siguiente frente seguro desde repo limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
