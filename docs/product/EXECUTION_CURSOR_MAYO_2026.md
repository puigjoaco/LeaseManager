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
| Frente activo | `codex/stage6-f22-certification-boundary`. |
| Fuente exacta | `main` en `3b72f0a6`, despues del merge confirmado de PR #912 `codex/company-bank-support-coverage`. |
| Brecha activa | El candidato F22 fixed-width local ya escribe/verifica archivo y manifest con entradas revisadas, pero el codigo empresa/cliente usado por el formato de registro seguia sin evidencia explicita de origen, revision y estado de autorizacion. Falta bloquear que un candidato local se declare listo para certificacion/presentacion SII por tener esos campos. |
| Motivo de prioridad | Etapa 6 avanza hacia artefactos F22 revisables/certificables sin abrir SII real. Antes de tratar el archivo como revisable, el codigo de certificacion debe quedar trazado, hasheado y separado de cualquier autorizacion real SII. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-f22-certification-boundary`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-f22-certification-boundary`. |
| Estado | Paquete en curso. Boundary de evidencia de codigo de certificacion F22 implementado y validado localmente; faltan commit, PR, CI, merge y limpieza. |
| Gate esperado | Este paquete no declara cierre Etapa 6, no certifica formato F22, no usa codigo real SII sin autorizacion, no presenta SII y no calcula impuesto final. Solo exige evidencia no sensible del codigo de certificacion usado por el candidato local y fuerza `ready_for_certification_submission=false`. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Formato/certificacion F22/DDJJ, codigo autorizado por SII, contenido tributario final y presentacion SII siguen bloqueados por formato/certificacion vigente aplicable, responsable tributario, autorizacion explicita y evidencia no sensible. `BLK-011` cobertura bancaria/leasing externa sigue como condicion de respaldo, no de este paquete. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Codigos reales/autorizaciones SII solo pueden referenciarse como refs no sensibles y con autorizacion actual; los candidatos locales deben permanecer no presentables. |
| Siguiente accion | Cerrar paquete con commit, PR, CI, merge y limpieza; si `main` contiene el merge, continuar con el siguiente frente seguro de Etapa 6. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
