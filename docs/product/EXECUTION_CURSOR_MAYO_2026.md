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
| Frente activo | Compliance datos sensibles / bootstrap de politicas de retencion. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `bootstrap_demo_compliance_policies` aplica `PoliticaRetencionDatos` con `update_or_create` sin validar `full_clean()` antes de persistir, permitiendo parametros invalidos o sensibles por bootstrap. |
| Motivo de prioridad | Compliance es el frente mas bajo aun parcial y esta brecha es local, verificable y no depende de secretos ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-policy-bootstrap-validation`. |
| Rama | `codex/compliance-policy-bootstrap-validation`. |
| Estado | Paquete implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Compliance local diagnostico/parcial; no cierre sin fuente autorizada y evidencia legal-operativa. |
| Estado al cerrar paquete | Validacion local completada: prueba focal de bootstrap Compliance, suite impactada Compliance/readiness, `manage.py check`, `makemigrations --check --dry-run`, gate Compliance local diagnostico/parcial, `npm ci`, `npm run build`, `npm run lint`, acceptance workflows e higiene previa. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si se reanuda esta sesion, continuar este worktree antes de abrir otro paquete. |
| Siguiente accion | Ejecutar higiene final, commit, PR, CI, merge, limpieza del worktree tactico y reset del cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
