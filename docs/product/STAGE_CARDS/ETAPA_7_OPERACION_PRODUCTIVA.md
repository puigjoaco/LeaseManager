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
- `run-postgres-restore-rehearsal.ps1` rechaza `OutputPath` dentro del repo
  fuera de `local-evidence/` antes de generar plan, tocar Docker o producir
  evidencia de restore.
- Auditoria local de observabilidad operativa con gates, integraciones,
  backlogs y senales runtime minimas.
- `audit_operational_observability` rechaza `--output` dentro del repo fuera
  de `local-evidence/` antes de auditar, para no versionar evidencia ni
  metadatos de observabilidad.
- Senales runtime persistidas para latencia mensual, cola/tareas, webhooks
  fallidos y crons fallidos, con evidencia y payload no sensibles; las claves
  de payload con forma de secreto o credencial tambien se rechazan.
- Para cierre productivo, las cuatro senales runtime obligatorias deben venir
  de `snapshot_controlado` o `real_autorizado`; mediciones locales, fixture o
  demo solo preparan el gate.
- API/backoffice autenticados exponen observabilidad operativa de solo lectura
  con referencias sensibles redactadas.
- Guard local de readiness Etapa 7 consolida observabilidad, restore, smoke
  publico, readiness de Reporting y aceptacion final sin ejecutar integraciones
  externas.
- El cierre productivo exige que Reporting este listo con `source_kind`
  `snapshot_controlado` o `real_autorizado`; readiness local, fixture o demo
  solo diagnostica.
- Smoke publico manual ejecutado con ambiente autorizado.
- El smoke publico es opt-in: `run-acceptance-workflows.ps1` no toca URLs
  externas por defecto, requiere `-RunPublicSmoke` o `-OnlySmoke` y URLs
  explicitas.
- La evidencia de smoke publico para cierre requiere `source_kind` autorizado
  y referencias no sensibles de autorizacion, ambiente y target/deploy; un
  resultado local o sintetico de cuatro roles solo prepara el gate.
- La aceptacion final para cierre requiere evidencia JSON autorizada con
  `accepted=true`, responsable, alcance/candidato, decision y referencias no
  sensibles; una referencia simple no reemplaza la aceptacion final.
- Restore probado.
- Bloqueos criticos cerrados.
- Aceptacion registrada.

## Salida

Producto listo para uso indefinido solo si todo componente obligatorio esta
implementado o confirmado, conectado, probado, documentado, auditado y aceptado.
