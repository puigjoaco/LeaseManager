# Runbook de cutover - mayo 2026

Este runbook define la preparacion para pasar de desarrollo controlado a uso
operable. No autoriza despliegues, migraciones ni cambios productivos por si
mismo.

## Precondiciones

- PRD rector definido sin ambiguedad.
- Etapas 1 a 7 cerradas o con excepciones aceptadas por escrito.
- Datos maestros validados.
- Backups y restore probados.
- Integraciones externas autorizadas y probadas en ambiente aislado.
- Secretos reprovisionados fuera del repo.
- CI deterministica verde.
- Smoke publico ejecutado manualmente con ambiente autorizado.
- Registro de evidencia completo.
- Bloqueos criticos cerrados o aceptados.

## Preflight

1. Confirmar rama, commit y tag candidato.
2. Confirmar estado de CI.
3. Confirmar variables de entorno por ambiente.
4. Confirmar plan de backup.
5. Confirmar plan de rollback.
6. Confirmar responsables disponibles.
7. Confirmar ventana de ejecucion.
8. Confirmar que no existen secretos versionados.
9. Confirmar que datos reales usados en pruebas estan autorizados.
10. Confirmar que integraciones externas no enviaran mensajes o documentos
    accidentales.
11. Confirmar que cualquier smoke publico fue solicitado con ambiente, URLs y
    responsable autorizados. La suite local deterministica no ejecuta smoke
    publico por defecto.
12. Confirmar rehearsal de restore PostgreSQL con datos sinteticos o restore
    autorizado reciente. El rehearsal local no reemplaza la prueba final con
    backup/snapshot autorizado.
13. Ejecutar auditoria local de observabilidad:
    `backend\.venv\Scripts\python.exe backend\manage.py audit_operational_observability`.

## Ejecucion controlada

1. Congelar cambios.
2. Generar backup.
3. Verificar restore o simulacro reciente.
4. Ejecutar migraciones aprobadas.
5. Ejecutar backfills aprobados, si existen.
6. Levantar servicios.
7. Ejecutar healthcheck/readiness y confirmar que las respuestas publicas no
   exponen detalles internos de DB, Redis, configuracion ni excepciones.
8. Ejecutar smoke operativo solo con autorizacion explicita:
   `scripts/run-acceptance-workflows.ps1 -RunPublicSmoke -FrontendUrl <url> -ApiBaseUrl <url>`.
9. Validar flujo minimo por rol.
10. Validar conciliacion o datos contables de muestra autorizada.
11. Validar documentos y reportes.
12. Registrar evidencia.

## Rollback

Rollback se activa si:

- falla healthcheck;
- falla autenticacion;
- falla migracion sin recuperacion inmediata;
- se detecta inconsistencia de datos;
- una integracion externa opera fuera de lo autorizado;
- existe riesgo de emision tributaria incorrecta;
- falla restore o backup esperado.

El rollback debe registrar causa, commit, ambiente, accion tomada, evidencia y
decision de reintento.

## Cierre

Cutover se considera listo solo cuando:

- todos los pasos tienen evidencia;
- no hay bloqueos criticos no aceptados;
- el responsable acepta el resultado;
- existe ruta de soporte y continuidad;
- el runbook queda actualizado con lo aprendido.

## Comandos seguros

- Acceptance deterministica local: `scripts/run-acceptance-workflows.ps1`.
- Acceptance sin smoke, equivalente CI: `scripts/run-acceptance-workflows.ps1 -SkipSmoke`.
- Smoke publico aislado: `scripts/run-acceptance-workflows.ps1 -OnlySmoke -FrontendUrl <url> -ApiBaseUrl <url>`.
- Plan de restore local sin tocar Docker: `scripts/run-postgres-restore-rehearsal.ps1 -PlanOnly`.
- Rehearsal PostgreSQL local con fixture sintetico:
  `scripts/run-postgres-restore-rehearsal.ps1`.
- Auditoria local de observabilidad operativa:
  `backend\.venv\Scripts\python.exe backend\manage.py audit_operational_observability`.
- Registrar senales runtime locales/controladas:
  `backend\.venv\Scripts\python.exe backend\manage.py record_operational_runtime_signal --signal-key <key> --status <status> --evidence-ref <ref> --value-json <json>`.

El smoke publico requiere URLs explicitas y el script Node rechaza destinos
externos si no recibe `--allow-external`, que el wrapper solo agrega cuando se
usa `-RunPublicSmoke` o `-OnlySmoke`.

El rehearsal de restore usa solo PostgreSQL local de `infra/docker-compose.yml`
y escribe evidencia bajo `local-evidence/`. No lee `.env`, no usa datos reales
y no cierra Operacion productiva sin restore de backup/snapshot autorizado.

La auditoria de observabilidad es read-only: agrega estado de gates,
integraciones, backlogs operativos y cobertura minima de senales runtime. No
conecta proveedores externos y no reemplaza monitoreo productivo.

Las senales runtime obligatorias son `monthly_calculation_latency`,
`queue_runtime`, `failed_webhooks` y `failed_crons`. Deben registrarse con
referencias no sensibles; una medicion local o sintetica prepara el gate, pero
el cierre productivo requiere medicion de ambiente real/controlado.
