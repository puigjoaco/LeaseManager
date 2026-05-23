# Bloqueos activos - mayo 2026

Este registro evita pendientes ocultos. Un bloqueo no es arquitectura de
producto ni debe redefinir dominios, entidades o dependencias. Un bloqueo no
impide documentar codigo, preparar gates o avanzar en trabajo seguro, pero
impide declarar cierre del frente afectado cuando falta evidencia.

| ID | Bloqueo | Tipo | Impacto | Desbloqueo requerido | Estado |
| --- | --- | --- | --- | --- | --- |
| BLK-001 | PRD Mayo 2026 debia promoverse como rector formal. | requiere_decision_usuario | Podia existir ambiguedad entre PRD vigente y candidato. | Promovido a `01_Set_Vigente/PRD_CANONICO.md`; PRD marzo archivado. | cerrado |
| BLK-002 | Falta validacion de datos reales o snapshot controlado para matriz contrato-propiedad-cuenta-facturacion. | bloqueado_dato_real | Etapa 1 no puede cerrarse. No impide preparacion segura ni correcciones que no usen datos/secretos no autorizados. El gate local `audit_stage1_matrix` ya existe, pero aun falta ejecutarlo contra snapshot controlado o DB real autorizada con refs trazables. | Entregar o autorizar `DATABASE_URL` de snapshot/control de datos y ejecutar `scripts/run-stage1-snapshot-gate.ps1` con `SourceKind snapshot_controlado` o `real_autorizado`, `SourceLabel`, `AuthorizationRef` y `ResponsibleRef` no sensibles; el wrapper aplica internamente `--require-data` y `--fail-on-violations`. | abierto |
| BLK-003 | Integraciones externas no estan abiertas por defecto. | bloqueado_externo | Email, WebPay, banco, UF, SII y storage no pueden declararse productivos. Email/WebPay quedan cubiertos por el gate Etapa 2 local con fuente autorizada y refs trazables para cierre; banco/Conciliacion quedan cubiertos por el gate Etapa 3 con fuente autorizada y refs trazables; SII queda cubierto por el gate Etapa 4 con fuente autorizada y refs trazables, pero no hay prueba productiva/sandbox autorizada. | Permisos, credenciales seguras, entorno aislado, pruebas y rollback. | abierto |
| BLK-004 | Reglas tributarias finales requieren validacion oficial o experta. | bloqueado_externo | SII, DTE, F29/F21, renta anual y certificados no pueden cerrarse por suposicion. Renta anual queda cubierta por el gate Etapa 6 con fuente autorizada y refs trazables, pero no hay validacion oficial/experta ni certificados controlados autorizados para cierre. | Validacion contra SII, normativa vigente o experto responsable. | abierto |
| BLK-005 | Politica final de firma/notaria y documentos operables debe cerrarse. | requiere_decision_usuario | Documentos y contratos no pueden cerrar totalmente. El flujo local ya exige PDF canonico y comprobante notarial emitido/formalizado/archivado antes de formalizar; el gate documental exige fuente autorizada, refs trazables y prueba PDF controlada para cierre. | Definir politica final, responsables, evidencia y prueba PDF controlada. | abierto |
| BLK-006 | Public smoke real esta separado de CI deterministica. | bloqueado_externo | Deploy/ambiente publico no se valida automaticamente y el smoke externo queda opt-in para evitar llamadas accidentales. | Ejecutar workflow manual con ambiente, URLs y responsable autorizados. | abierto |
| BLK-007 | Migracion desde savegames debe mantenerse read-only hasta autorizacion. | requiere_decision_usuario | No se puede backfillear ni transformar datos reales. | Preflight, backup, rollback y confirmacion explicita. | abierto |
| BLK-008 | Artefactos legacy versionados aun contienen datos y overrides sensibles de migracion. | requiere_decision_usuario | No pueden usarse como evidencia final ni como fuente productiva sin control adicional. El root activo bloquea regresion de `.env`, DBs, bundles generados, dumps, snapshots, certificados y evidencia local versionada con `scripts/assert-repo-hygiene.ps1`; ademas, el exportador y los reportes de runners/rehearsals/verificacion rechazan salidas dentro del repo fuera de `migration/bundles/` antes de leer legacy, bundles o DBs, y los wrappers de readiness Etapa 1-7 rechazan outputs dentro del repo fuera de `local-evidence/` antes de generar auditorias. Historial Git/savegames siguen siendo fuentes sensibles. | Redactar, mover a snapshot controlado/manifest seguro o confirmar alcance autorizado de esos artefactos; si se requiere purga de historial, pedir decision explicita porque reescribe Git. | abierto |
| BLK-009 | El paquete `codex/stage1-migration-config-gates` debia integrarse a `main`. | resuelto_confirmado | PR #9 paso `Release Gate / acceptance`, fue mergeado por squash en `main` como `5d62ee5` y el root limpio fue actualizado. | Completado; mantener `main` sincronizado y crear nuevos worktrees solo para el siguiente frente. | cerrado |
| BLK-010 | Falta cierre legal-operativo de `Compliance.DatosPersonalesChile2026`. | bloqueado_externo | Compliance de datos personales no puede declararse cerrado sin politica aprobada, responsables designados, controles implementados, evidencia archivada, validacion legal-operativa y fuente autorizada. No impide preparar validadores internos ni corregir metadata sensible. | Ejecutar `scripts/run-compliance-data-readiness-gate.ps1` con `SourceKind snapshot_controlado` o `real_autorizado`, `SourceLabel`, `AuthorizationRef`, `PolicyApprovalRef`, `ResponsibleRef`, `ControlsEvidenceRef`, `ArchivedEvidenceRef` y `LegalReviewRef` no sensibles, usando fuente controlada/autorizada; posterior al 2026-12-01, resolver readiness o registrar suspension formal. | abierto |

## Detalle operativo de `BLK-002` - 2026-05-21

Inventario metadata-only ejecutado desde el root limpio, sin abrir contenidos ni
imprimir secretos, dumps, filas, RUTs, cuentas ni datos bancarios completos.

Verificacion reproducible desde `main` vigente:

- `scripts/run-stage1-snapshot-gate.ps1` contra SQLite local vacio migrado en
  `local-evidence/` falla correctamente con `stage1.data_missing`.
- `scripts/run-acceptance-workflows.ps1` ejecuta el readiness local de Etapa 1
  como diagnostico `source_kind=local`; protege que la falta de fuente
  autorizada no derive en solicitud repetida de secretos ni en una fuente
  controlada simulada.
- `scripts/run-acceptance-workflows.ps1` tambien ejecuta el snapshot gate de
  Etapa 1 contra SQLite vacio bajo `local-evidence/` y exige que falle como
  `bloqueado_dato_real` con `stage1.data_missing`, sin declarar cierre.
- `scripts/run-acceptance-workflows.ps1` protege que `real_autorizado` con
  `-RunMigrations` falle antes de generar JSON, para no permitir migraciones
  desde este gate contra una fuente real.
- Resultado del readiness local: `classification=implementado_sin_evidencia`,
  `evidence_grade=false`, `ready_for_stage1_close=false`,
  `has_required_stage1_data=false`.
- Resultado del gate evidencial vacio: `classification=bloqueado_dato_real`,
  `ready_for_stage1_close=false` y issue `stage1.data_missing`.
- El JSON del gate evidencial incluye `aggregate_classification`; en la
  verificacion vacia los agregados requeridos quedan `bloqueado_dato_real` y
  los agregados opcionales sin filas quedan `implementado_sin_evidencia`.
- El auditor bloquea fuentes evidenciales sin `SourceLabel`,
  `AuthorizationRef` o `ResponsibleRef` trazables, o con valores sensibles, y
  redacta valores invalidos antes de escribir el JSON.
- El wrapper y el comando Django rechazan outputs dentro del repo fuera de
  `local-evidence/`, para no versionar evidencia ni metadatos de auditoria.
- Esta verificacion confirma que el gate funciona y que no existe evidencia de
  cierre sin una fuente `snapshot_controlado` o `real_autorizado` autorizada.

Fuentes candidatas externas detectadas:

- `D:/Proyectos/LeaseManager-Produccion-1.0/backend/.env` y
  `D:/Proyectos/LeaseManager-Produccion-1.0/backend/.env.supabase-staging.local`:
  posible origen de `DATABASE_URL` o credencial legacy. Clasificacion:
  `requiere_decision_usuario` y `bloqueado_externo`; no se puede leer ni usar
  sin autorizacion explicita.
- `D:/Proyectos/LeaseManager-Produccion-1.0/backend/*.sqlite3` y
  `D:/Proyectos/LeaseManager-Produccion-1.0/backend/*.db`: bases historicas o
  de prueba detectadas por metadata. Clasificacion: `bloqueado_dato_real`;
  deben ser autorizadas y clasificadas como `snapshot_controlado` o descartadas
  antes de ejecutar cualquier gate.
  - Relectura schema-only read-only del 2026-05-21, sin filas ni valores:
    `bundle-inspect-final.db`, `bundle-inspect.db`, `dev-bootstrap.sqlite3`,
    `review-check.sqlite3`, `test-compliance-bootstrap.sqlite3`,
    `test-control-activity.sqlite3`, `test-showcase-access.sqlite3`,
    `test-showcase-empty.sqlite3`, `test-tax-annual-flow.sqlite3` y
    `test-tax-monthly-flow.sqlite3` exponen tablas canonicas de Etapa 1
    (`patrimonio_*`, `operacion_*`, `contratos_*`, `cobranza_*`,
    `conciliacion_ingresodesconocido`, `contabilidad_*`, `sii_*`). Esto solo
    prueba compatibilidad de esquema; no prueba que contengan datos reales,
    snapshot controlado ni matriz valida.
  - `review-fixes.sqlite3`, `review-focused.sqlite3`,
    `test-codex-contract-code.sqlite3`, `test-codex-mandate-limit.sqlite3`,
    `test-codex-migrations.sqlite3` y `test-codex.db` son archivos vacios por
    metadata y quedan descartados como fuente directa.
- `D:/Proyectos/LeaseManager-clean/infobackend/*.csv` y `*.sql`: exports
  legacy de empresas, socios, propiedades, contratos, cuentas y
  participaciones. Clasificacion: `requiere_decision_usuario`; sirven como
  insumo de transformacion read-only, no como cierre directo de Etapa 1.
- `D:/Proyectos/LeaseManager-savegame-20260520-082940/untracked-files/.Codex/context/excel-mayo-2026/Calculadora desde Nov 2023.xlsx`
  y metadata `.codex-spreadsheet/*.json`: referencia operativa del Excel Mayo
  2026. Clasificacion: `requiere_decision_usuario`; puede contrastar reglas y
  casos, pero no reemplaza el gate contra snapshot/base autorizada.
- `D:/Proyectos/LeaseManager-savegame-20260520-082940/untracked-files/docs/production-readiness/sql/etapa1_*.sql`
  y `supabase/migrations/*.sql`: scripts historicos de preflight/export/rollback
  y migracion legacy. Clasificacion: `parcial`; pueden orientar un preflight
  read-only, pero el modelo canonico Django/PostgreSQL del root limpio manda.

Proxima accion concreta: el usuario debe autorizar una de estas rutas de
desbloqueo:

1. Ingresar un `DATABASE_URL` seguro para `snapshot_controlado` y ejecutar
   `scripts/run-stage1-snapshot-gate.ps1 -SourceKind snapshot_controlado` con
   `SourceLabel`, `AuthorizationRef` y `ResponsibleRef` no sensibles.
   Ese wrapper llama a `audit_stage1_matrix` con datos obligatorios y falla si
   encuentra violaciones de gate.
2. Autorizar lectura puntual de un `.env` legacy solo para extraer una URL de
   snapshot/staging, sin imprimirla ni versionarla.
3. Autorizar una base `.sqlite3`/`.db` historica como candidato de
   `snapshot_controlado` para clasificacion read-only previa.
4. Autorizar construccion de snapshot controlado desde CSV/SQL/Excel legacy con
   preflight, transformacion trazada, backup/rollback si aplica y sin declarar
   cierre hasta que pase el gate.

Regla anti-bucle: si ninguna ruta fue autorizada y el estado no cambio, no se
debe repetir indefinidamente la misma solicitud. El frente sigue sin cierre,
pero el trabajo debe cambiar a preparacion segura, integracion, documentacion
de una nueva brecha real o una unica pregunta concreta.

## Regla de uso

Todo bloqueo nuevo debe indicar tipo, impacto, desbloqueo requerido y estado.
Si un cambio implementa codigo bloqueado por dato o servicio externo, el estado
del frente sigue siendo `implementado_sin_evidencia` hasta ejecutar el gate.
