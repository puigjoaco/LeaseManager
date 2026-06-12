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
| Frente activo | Sin frente activo persistente. Ultimo paquete local preparado: Etapa 4 / SII - normalizacion antes de `full_clean()`. |
| Fuente exacta | Base `main` limpia en `57b4d182`; paquete trabajado en worktree tactico `D:/Proyectos/LeaseManager-stage4-sii-full-clean-normalization` y rama `codex/stage4-sii-full-clean-normalization`; rescue pausado fuera de alcance. |
| Brecha activa | Ninguna persistente en cursor. La brecha preparada normaliza refs/textos SII antes de que `full_clean()` ejecute validadores de campo. |
| Motivo de prioridad | Paquete local, pequeno y verificable; alinea SII con el hardening aplicado en Canales, Conciliacion, Contabilidad y Documentos sin conectar SII, certificados, secretos ni datos reales. |
| Worktree | Ninguno activo de producto al reanudar; confirmar con `git worktree list`. |
| Rama | Ninguna activa de producto al reanudar; confirmar con `git status --short --branch`. |
| Estado | Validacion local completa del paquete SII; continuar solo desde estado real de `main` y PR/CI/merge confirmados. |
| Gate esperado | Gate local Etapa 4 queda `classification=parcial`, `ready_for_stage4_sii=false`, sin cierre evidencial falso. |
| Estado al cerrar paquete | Focal SII OK; suite impactada SII/readiness OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 4 parcial OK; frontend build/lint OK; acceptance local OK. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; si solo aparece el rescue pausado, continuar con el siguiente paquete pequeno, local, verificable y cerrable sin tocar esos archivos. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
