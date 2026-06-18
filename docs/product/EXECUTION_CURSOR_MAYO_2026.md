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
| Frente activo | `codex/stage6-export-materializer`. |
| Fuente exacta | `main` en `a8ca0a77`, despues del merge confirmado de PR #918 `codex/stage6-review-decision-ui`. |
| Brecha activa | `AnnualTaxExport` ya conserva manifiesto y paquete local materializable/verificable, pero faltaba una herramienta operativa que escribiera esos archivos desde un export preparado y los verificara inmediatamente sin usar rutas versionables. |
| Motivo de prioridad | Para pasar de previews internos a salidas exportables/controladas, el responsable necesita una forma repetible de materializar archivos locales DDJJ/F22 y comprobar hash, manifest y boundary antes de cualquier revision/presentacion. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-export-materializer`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-export-materializer`. |
| Estado | Paquete en curso. Se agrega comando controlado para materializar/verificar el paquete local de `AnnualTaxExport` bajo `local-evidence/` o fuera del repo, rechazando salidas versionables dentro del repo. |
| Gate esperado | Este paquete no declara formato oficial certificado, no presenta SII, no calcula impuesto final y no usa datos reales. Solo convierte un `AnnualTaxExport` preparado en archivos locales verificables para revision controlada. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | La decision tributaria final, formato/certificacion F22/DDJJ, codigo autorizado por SII, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita, formato/certificacion vigente aplicable y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. La aprobacion para presentacion solo puede existir como decision y evidencia trazables no sensibles; nunca como salida automatica del motor local. |
| Siguiente accion | Ejecutar tests focales del comando, suite impactada Etapa 6/SII, gate Etapa 6, acceptance proporcional, higiene y diff; si pasa, cerrar paquete con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
