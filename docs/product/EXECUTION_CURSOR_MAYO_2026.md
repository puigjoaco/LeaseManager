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
| Frente activo | `codex/stage6-at2025-compatibility`. |
| Fuente exacta | `main` en `f473dada`, despues del merge confirmado de PR #926 `codex/stage6-company-review-api`. |
| Brecha activa | La matriz de compatibilidad oficial de Etapa 6 estaba centrada en AT2026, pero el objetivo operativo exige confirmar compatibilidad/formato/upload/API para AT2025 y AT2026 sin asumir API ni formato oficial inexistente. |
| Motivo de prioridad | AC2024/AT2025 y AC2025/AT2026 deben poder avanzar con una lectura oficial separada por ano tributario: si SII solo prueba certificacion o rutas de archivo/upload, LeaseManager debe registrar eso y dejar brechas explicitas antes de producir salidas oficiales. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-at2025-compatibility`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-at2025-compatibility`. |
| Estado | Paquete en ejecucion: parametrizar `build_stage6_official_compatibility_matrix()` para AT2025/AT2026, registrar fuentes SII publicas no sensibles por ano y mantener como brecha explicita cualquier formato F22 no confirmado por fuente oficial segura. |
| Gate esperado | Este paquete solo usa URLs publicas SII y metadata no sensible. No lee `.env`, DB real, documentos reales, EDIG ejecutable, banco ni SII autenticado; no declara formato oficial final, calculo tributario final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Carga productiva real, documentos completos, formato/certificacion F22/DDJJ aplicable, codigo autorizado por SII, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita, formato/certificacion vigente aplicable y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. La aprobacion para presentacion solo puede existir como decision y evidencia trazables no sensibles; nunca como salida automatica del motor local. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, registrar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el siguiente frente seguro desde repo limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
