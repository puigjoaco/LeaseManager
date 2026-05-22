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
