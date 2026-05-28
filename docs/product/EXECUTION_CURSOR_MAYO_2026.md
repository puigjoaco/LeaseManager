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
| Frente activo | Etapa 5 / Documentos - guard de endpoint generico para PDF generado. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El endpoint generico de documentos bloqueaba crear `origen=generado_sistema`, pero aun podia convertir un documento externo a generado o mutar un PDF generado ya emitido. |
| Motivo de prioridad | La stage card exige que la emision de PDF generado ocurra solo por `generar-pdf/`, con preview y auditoria dedicada; el endpoint generico no debe simular ni alterar ese origen. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-generated-document-generic-guard`. |
| Rama | `codex/stage5-generated-document-generic-guard`. |
| Estado | Paquete abierto en implementacion local. |
| Gate esperado | Readiness documental local debe permanecer `classification=parcial`, `ready_for_stage5_documents=false` por fuente local no autorizada; las pruebas API deben bloquear mutaciones genericas de documentos generados por sistema. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta validacion, PR, CI, merge y limpieza; no abrir otro frente mientras este paquete este sucio. |
| Siguiente accion | Ejecutar pruebas focales e impactadas, gate documental local, acceptance local, higiene, PR/CI/merge y cierre del cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
