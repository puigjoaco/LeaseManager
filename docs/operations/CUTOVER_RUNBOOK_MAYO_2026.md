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
11. Confirmar que cualquier smoke publico fue solicitado con ambiente, URLs,
    responsable y referencias de evidencia no sensibles autorizados. La suite
    local deterministica no ejecuta smoke publico por defecto.
12. Confirmar rehearsal de restore PostgreSQL con datos sinteticos o restore
    autorizado reciente. El rehearsal local no reemplaza la prueba final con
    backup/snapshot autorizado.
13. Ejecutar auditoria local de observabilidad:
    `backend\.venv\Scripts\python.exe backend\manage.py audit_operational_observability`.
14. Ejecutar guard local de readiness Etapa 7:
    `scripts/run-stage7-readiness-gate.ps1`. El cierre requiere ademas
    evidencia de restore de backup/snapshot autorizado, smoke publico
    autorizado y aceptacion final autorizada.
15. Ejecutar auditoria local de readiness documental si el paquete incluye
    documentos contractuales:
    `backend\.venv\Scripts\python.exe backend\manage.py audit_document_readiness`.

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
   `scripts/run-acceptance-workflows.ps1 -RunPublicSmoke -FrontendUrl <url> -ApiBaseUrl <url> -PublicSmokeAuthorizationRef <ref> -PublicSmokeEnvironmentRef <ref> -PublicSmokeTargetRef <ref>`.
9. Validar flujo minimo por rol.
10. Validar conciliacion o datos contables de muestra autorizada.
11. Validar documentos y reportes.
12. Registrar evidencia.
13. Registrar aceptacion final con `accepted=true`, responsable, alcance,
    decision y referencias no sensibles.

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
- Smoke publico aislado: `scripts/run-acceptance-workflows.ps1 -OnlySmoke -FrontendUrl <url> -ApiBaseUrl <url> -PublicSmokeAuthorizationRef <ref> -PublicSmokeEnvironmentRef <ref> -PublicSmokeTargetRef <ref>`.
- Plan de restore local sin tocar Docker: `scripts/run-postgres-restore-rehearsal.ps1 -PlanOnly`.
- Rehearsal PostgreSQL local con fixture sintetico:
  `scripts/run-postgres-restore-rehearsal.ps1`.
- Guard local de readiness Etapa 7:
  `scripts/run-stage7-readiness-gate.ps1`.
- Auditoria local de observabilidad operativa:
  `backend\.venv\Scripts\python.exe backend\manage.py audit_operational_observability`.
- Auditoria local de readiness documental:
  `backend\.venv\Scripts\python.exe backend\manage.py audit_document_readiness`.
- Registrar senales runtime locales/controladas:
  `backend\.venv\Scripts\python.exe backend\manage.py record_operational_runtime_signal --signal-key <key> --status <status> --evidence-ref <ref> --value-json <json>`.

El smoke publico requiere URLs explicitas y el script Node rechaza destinos
externos si no recibe `--allow-external`, que el wrapper solo agrega cuando se
usa `-RunPublicSmoke` o `-OnlySmoke`. Para que esa salida sirva como evidencia
de cierre de Etapa 7, debe emitirse con `source_kind`/`smoke_source_kind`
`public_smoke_autorizado`, `ambiente_autorizado`, `staging_autorizado` o
`real_autorizado`, mas `authorization_ref`, `environment_ref` y
`target_ref`/`deployment_ref` no sensibles; URLs, tokens o credenciales no son
referencias validas.

El rehearsal de restore usa solo PostgreSQL local de `infra/docker-compose.yml`
y escribe evidencia bajo `local-evidence/`. No lee `.env`, no usa datos reales
y no cierra Operacion productiva sin restore de backup/snapshot autorizado.

La auditoria de observabilidad es read-only: agrega estado de gates,
integraciones, backlogs operativos y cobertura minima de senales runtime. No
conecta proveedores externos y no reemplaza monitoreo productivo.

El guard local de readiness Etapa 7 es read-only y consolida evidencias. Sin
argumentos debe quedar `classification=parcial`: no ejecuta smoke publico,
no conecta proveedores externos y no cierra Operacion productiva sin
restore de backup/snapshot autorizado, smoke autorizado, observabilidad lista y
aceptacion final autorizada. Un rehearsal sintetico con `restore_verified=true`
prepara el gate, pero no reemplaza una evidencia de restore con
`source_kind`/`restore_source_kind` en `snapshot_controlado`,
`real_autorizado`, `backup_autorizado` o `restore_autorizado`, mas
`authorization_ref` y `backup_ref`/`backup_file` no sensibles. Del mismo modo,
un arreglo de resultados de smoke con cuatro roles OK no cierra Operacion
productiva si no viene envuelto como evidencia de ambiente autorizado con
`authorization_ref`, `environment_ref` y `target_ref`/`deployment_ref` no
sensibles. Una referencia simple de aceptacion final prepara trazabilidad, pero
el cierre exige evidencia JSON con `accepted=true`,
`source_kind`/`final_acceptance_source_kind` en
`aceptacion_final_autorizada`, `final_acceptance_autorizada`,
`cutover_autorizado`, `ambiente_autorizado` o `real_autorizado`, mas
`authorization_ref`, `responsible_ref`, `scope_ref`/`release_candidate_ref` y
`acceptance_ref`/`decision_ref`/`signoff_ref` no sensibles.

La auditoria documental es read-only: no abre storage ni PDFs reales. Consolida
politicas activas por tipo documental, metadata obligatoria, referencias no
sensibles a politica final, responsables y prueba PDF controlada.

Las senales runtime obligatorias son `monthly_calculation_latency`,
`queue_runtime`, `failed_webhooks` y `failed_crons`. Deben registrarse con
referencias no sensibles; una medicion local o sintetica prepara el gate, pero
el cierre productivo requiere medicion de ambiente real/controlado.
