# Bitacora operativa - mayo 2026

Este archivo conserva el frente activo de ejecucion. No reemplaza al PRD,
AGENTS, fuente de verdad, arquitectura, matriz, stage cards, evidencia ni
bloqueos. Su funcion es evitar que una reanudacion convierta contexto auxiliar
en tarea nueva.

El nombre del archivo se mantiene por compatibilidad con `AGENTS.md`; su uso es
de bitacora operativa, no de prompt persistente ni fuente de autorizaciones.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer esta bitacora.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita aqui o descartar con instruccion segura antes de abrir un frente
  distinto.
- Solo el estado real del repo y esta bitacora definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.
- Si esta bitacora nombra una rama/worktree ya cerrados y `main` contiene el
  merge correspondiente, no recrear el paquete anterior: tratarlo como cerrado,
  corregir esta bitacora y continuar con el siguiente frente seguro.

## Frente activo

| Campo | Valor |
| --- | --- |
| Frente activo | `codex/stage6-export-package-verifier`. |
| Fuente exacta | `main` en `56882c23`, despues del merge confirmado de PR #902 `codex/stage6-export-file-package`. |
| Brecha activa | Etapa 6 ya materializa un paquete local DDJJ/F22; falta revalidar desde disco que `manifest.json` y archivos JSON coinciden con el `AnnualTaxExport` esperado, sin permitir archivos extra ni ruptura del boundary oficial. |
| Motivo de prioridad | El objetivo pide pasar de artefactos comparables a salidas exportables/certificables o revisables. Verificar el paquete escrito desde disco es la siguiente capa antes de hablar de formato oficial SII, upload o certificacion. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-export-package-verifier`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-export-package-verifier`. |
| Estado | Paquete en curso solo mientras esta rama/worktree exista. Validaciones locales completas: focal 2 tests OK, impactada 325 tests OK, gate Etapa 6 parcial esperado, frontend build/lint OK, acceptance 1513 tests OK, higiene y diff-check OK. Faltan commit, PR, CI, merge y limpieza. |
| Gate esperado | Este paquete no declara cierre de Etapa 6 ni genera archivo oficial SII. Solo agrega verificacion local de paquete JSON materializado para revision controlada. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Formato/certificacion F22, DDJJ y presentacion SII siguen bloqueados por fuente oficial/certificacion vigente, responsable tributario y autorizacion explicita. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Completar documentos, validaciones proporcionales y cierre por PR/CI/merge/limpieza si pasa. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
