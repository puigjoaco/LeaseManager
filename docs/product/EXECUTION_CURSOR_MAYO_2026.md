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
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Sin paquete tactico abierto tras cerrar el paquete Etapa 4 SII - responsable de revision para F29 mensual. |
| Fuente exacta | `main` debe quedar limpio tras el merge del paquete; PRD vigente, stage cards 4/5/6/7 y matriz de trazabilidad fijan contabilidad/tributacion asistida con responsable trazado antes de estados avanzados. |
| Brecha activa | Ninguna brecha tactica abierta en este cursor. |
| Motivo de prioridad | Evitar que reanudaciones o compactaciones reabran el paquete F29 ya implementado: F29 mensual avanzado conserva responsable no sensible y no existe accion ciega de estado sin responsable. |
| Worktree | N/A tras limpieza del paquete. |
| Rama | `main` tras merge y limpieza. |
| Estado | Paquete Etapa 4 F29 responsable implementado, validado localmente y documentado; no declarar cierre de Etapa 4 sin fuente `snapshot_controlado` o `real_autorizado`, ambiente SII/regla fiscal autorizada y evidencia final. |
| Gate esperado | Para el siguiente paquete, repetir protocolo: diagnosticar desde repo limpio, elegir el siguiente frente seguro por trazabilidad, usar worktree `codex/...`, validar proporcionalmente, actualizar evidencia/trazabilidad si aplica y cerrar con PR/CI/merge/limpieza. |
| Estado al cerrar paquete | F29 mensual en estados aprobados, observados o rectificados exige `borrador_ref` y `responsable_revision_ref` no sensibles en dominio/API/backoffice/readiness; snapshots/admin/API redactan refs sensibles. |
| Bloqueos relacionados | Etapa 4/6 no cierran sin ambiente SII real/controlado, validacion oficial/experta, fuente `snapshot_controlado` o `real_autorizado` y evidencia final. Es condicion de cierre, no freno para preparar siguientes paquetes locales. |
| Politica de reanudacion | No reabrir el paquete F29 ni redactar goals. Si `main` esta limpio, seleccionar el siguiente frente seguro desde AGENTS, PRD, matriz, stage cards y evidencia. No pedir `.env`, certificados SII ni datos reales salvo solicitud concreta del usuario. |
| Siguiente accion | Tras merge y limpieza, continuar con el siguiente frente local seguro segun orden y trazabilidad vigentes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
