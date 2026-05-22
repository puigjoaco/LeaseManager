# Etapa 7 - Operacion productiva

## Objetivo

Dejar el sistema operable para uso continuo con backup, restore, monitoreo,
runbook, smoke y aceptacion.

## Alcance

- Infraestructura.
- Deploy autorizado.
- Backups y restore.
- Monitoreo y logs.
- Seguridad, RBAC y auditoria.
- Runbook de soporte.
- Aceptacion final.

## Gate

- Etapas previas cerradas o excepciones aceptadas.
- CI deterministica verde.
- Healthcheck/readiness publicos sin exposicion de detalles internos de
  dependencias ante falla.
- Rehearsal de restore PostgreSQL local con datos sinteticos y evidencia bajo
  `local-evidence/`, antes de la prueba final con backup/snapshot autorizado.
- Auditoria local de observabilidad operativa con gates, integraciones,
  backlogs y senales runtime minimas.
- Senales runtime persistidas para latencia mensual, cola/tareas, webhooks
  fallidos y crons fallidos, con evidencia no sensible.
- Smoke publico manual ejecutado con ambiente autorizado.
- El smoke publico es opt-in: `run-acceptance-workflows.ps1` no toca URLs
  externas por defecto, requiere `-RunPublicSmoke` o `-OnlySmoke` y URLs
  explicitas.
- Restore probado.
- Bloqueos criticos cerrados.
- Aceptacion registrada.

## Salida

Producto listo para uso indefinido solo si todo componente obligatorio esta
implementado o confirmado, conectado, probado, documentado, auditado y aceptado.
