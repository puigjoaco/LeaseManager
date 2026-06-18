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
| Frente activo | `codex/company-bank-support-coverage`. |
| Fuente exacta | `main` en `1676efed`, despues del merge confirmado de PR #911 `codex/stage6-ddjj-zip-candidate`. |
| Brecha activa | La contabilidad/renta ya puede medir avance interno y generar artefactos anuales locales, pero aun necesita una capa segura para convertir respaldos bancarios/leasing externos en cobertura documental verificable. Falta auditar operaciones, categorias de respaldo, confirmacion bancaria y faltantes sin versionar adjuntos ni PII. |
| Motivo de prioridad | El objetivo pide pasar desde artefactos comparables a salidas revisables/exportables con respaldo suficiente. Antes de declarar que contabilidad/renta puede revisar leasing, la evidencia bancaria debe quedar medida con manifiesto redactado y sus faltantes explicitados. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-company-bank-support-coverage`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/company-bank-support-coverage`. |
| Estado | Paquete en curso. Implementado auditor/command y documentacion de boundary; faltan validaciones completas, docs finales, commit, PR, CI, merge y limpieza. |
| Gate esperado | Este paquete no declara cierre contable/renta, no lee adjuntos reales desde Git, no presenta SII ni abre banco. Solo audita un manifiesto redactado de respaldo bancario/leasing y registra cobertura/faltantes para revision responsable. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | `BLK-011` cobertura bancaria/leasing externa requiere manifiesto redactado autorizado y auditado; formato/certificacion F22/DDJJ, contenido tributario final y presentacion SII siguen bloqueados por formato/certificacion vigente aplicable, responsable tributario, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Facturas, adjuntos y correos reales quedan fuera de Git; usar manifiestos redactados bajo `local-evidence/` o fuente externa controlada solo con autorizacion vigente. |
| Siguiente accion | Ejecutar suite impactada y acceptance proporcional; si pasa, cerrar paquete con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
