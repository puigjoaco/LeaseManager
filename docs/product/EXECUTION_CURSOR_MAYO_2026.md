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
| Frente activo | `codex/stage6-export-destination-guard`. |
| Fuente exacta | `main` en `d8987377`, despues del merge confirmado de PR #920 `codex/stage6-f22-candidate-materializer`. |
| Brecha activa | El materializador local de `AnnualTaxExport` escribe y verifica paquetes DDJJ/F22, pero el writer aceptaba directorios destino existentes y podia mezclar restos locales previos antes de que el verifier fallara. |
| Motivo de prioridad | Los paquetes exportables deben ser evidencia local reproducible: una corrida nueva no puede sobrescribir ni combinar archivos anteriores, incluso bajo `local-evidence/` o rutas externas controladas. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-export-destination-guard`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-export-destination-guard`. |
| Estado | Paquete revalidado localmente sobre `main` actual. Se endurece `write_annual_tax_export_file_package` para rechazar destinos no directorio o directorios no vacios antes de escribir cualquier archivo, y se cubre desde el comando de materializacion. Pendiente solo CI remoto, merge y limpieza. |
| Gate esperado | Este paquete no declara formato oficial certificado, no presenta SII, no calcula impuesto final y no usa datos reales. Solo garantiza que la evidencia local materializada parte desde un destino limpio y controlado. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | La decision tributaria final, formato/certificacion F22/DDJJ, codigo autorizado por SII, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita, formato/certificacion vigente aplicable y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. La aprobacion para presentacion solo puede existir como decision y evidencia trazables no sensibles; nunca como salida automatica del motor local. |
| Siguiente accion | Actualizar PR #921 con el commit rebaseado, esperar CI remoto, mergear y limpiar rama/worktree. Si `main` ya contiene el merge de este frente, no reabrirlo: tomar el siguiente frente seguro desde repo limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
