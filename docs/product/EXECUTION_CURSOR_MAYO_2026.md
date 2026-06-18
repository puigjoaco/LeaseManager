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
| Frente activo | `codex/stage6-ddjj-ascii-candidate`. |
| Fuente exacta | `main` en `f58b8a2c`, despues del merge confirmado de PR #909 `codex/stage6-f22-mapping-entries`. |
| Brecha activa | `AnnualTaxExport` materializa DDJJ como JSON local revisable, pero DDJJ aun no tiene candidato ASCII posicional por formulario alineado con la ruta oficial de transferencia/software. Falta una capa que tome `AnnualTaxDDJJFormLayout` preparado, matriz DDJJ/F22 y registros revisados para producir/verificar un archivo candidato DDJJ estructural. |
| Motivo de prioridad | El objetivo pide archivos exportables/certificables para SII o revision/presentacion controlada. Despues de F22 fixed-width, el siguiente avance directo es acercar DDJJ a archivo candidato verificable sin asumir API ni presentar SII. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-ddjj-ascii-candidate`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-ddjj-ascii-candidate`. |
| Estado | Paquete en curso solo mientras esta rama/worktree exista. Faltan implementacion, docs/evidencia, validaciones, commit, PR, CI, merge y limpieza. |
| Gate esperado | Este paquete no declara cierre de Etapa 6, no presenta SII ni produce calculo tributario final. Solo construye un candidato DDJJ ASCII posicional local si el layout preparado trae largo/refs/fuente, el export contiene items DDJJ del formulario y los registros revisados cumplen estructura ASCII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Formato/certificacion F22/DDJJ, contenido tributario final y presentacion SII siguen bloqueados por formato/certificacion vigente aplicable, responsable tributario, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Implementar contrato/candidato DDJJ ASCII posicional desde layout preparado y registros revisados, tests, docs/evidencia y cierre por PR/CI/merge/limpieza si pasa. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
