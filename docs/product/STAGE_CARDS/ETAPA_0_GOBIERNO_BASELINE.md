# Etapa 0 - Gobierno y baseline

## Objetivo

Dejar claro que manda, como se trabaja, cual es el baseline tecnico y que
evidencia respalda el root limpio.

## Entradas

- `AGENTS.md`
- `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`
- `docs/governance/CODEX_OPERATING_PROTOCOL_MAYO_2026.md`
- `docs/product/EXECUTION_CURSOR_MAYO_2026.md`
- `docs/RELEASE_GATE_BASELINE_MAYO_2026.md`
- CI en `main`

## Gate

- Fuente de verdad sin ambiguedad.
- Worktree policy documentada.
- Cursor operativo vigente para reanudaciones, worktrees y metatareas cerradas.
- Artefactos locales de herramienta quedan fuera del versionado y no deben
  ensuciar `git status` del root limpio ni confundirse con paquete activo.
- Superficies publicas con errores seguros, sin mensajes internos ni nombres de
  configuracion expuestos.
- CI deterministica verde.
- Savegames preservados read-only.
- Registro de evidencia inicial actualizado.

## Salida

Estado minimo: `resuelto_confirmado` para gobierno base. El PRD Mayo 2026 ya
esta promovido como rector; cualquier nueva decision de producto debe
registrarse como cambio al PRD vigente o bloqueo concreto.
