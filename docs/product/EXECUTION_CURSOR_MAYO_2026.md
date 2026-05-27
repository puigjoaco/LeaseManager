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
| Frente activo | Patrimonio / representaciones futuras. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `RepresentacionComunidad` valida representantes patrimoniales solo contra participaciones vigentes hoy, por lo que una representacion futura puede quedar invalida aunque el socio tenga participacion activa durante esa ventana futura. |
| Motivo de prioridad | Etapa 1/Patrimonio es el siguiente frente temprano por trazabilidad; la correccion es local, verificable y no requiere fuentes externas. |
| Worktree | `D:/Proyectos/LeaseManager-patrimonio-future-representation-participant`. |
| Rama | `codex/patrimonio-future-representation-participant`. |
| Estado | Paquete abierto para alinear representaciones patrimoniales futuras con participaciones efectivas en la misma ventana. |
| Gate esperado | Focal Patrimonio/auditor; suite `patrimonio core.tests_stage1_matrix_audit`; `manage.py check`; `makemigrations --check --dry-run`; frontend build/lint; acceptance; higiene repo. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Implementar y validar representaciones futuras con participante patrimonial vigente en la ventana programada. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
