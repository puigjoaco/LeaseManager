# Etapa 0 - Gobierno y baseline

## Objetivo

Dejar claro que manda, como se trabaja, cual es el baseline tecnico y que
evidencia respalda el root limpio.

## Entradas

- `AGENTS.md`
- `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`
- `docs/governance/CODEX_OPERATING_PROTOCOL_MAYO_2026.md`
- `docs/RELEASE_GATE_BASELINE_MAYO_2026.md`
- CI en `main`

## Gate

- Fuente de verdad sin ambiguedad.
- Worktree policy documentada.
- CI deterministica verde.
- Savegames preservados read-only.
- Registro de evidencia inicial actualizado.

## Salida

Estado minimo: `resuelto_confirmado` para gobierno base. Si falta decidir el
PRD candidato, registrar `requiere_decision_usuario` sin bloquear la codebase.
