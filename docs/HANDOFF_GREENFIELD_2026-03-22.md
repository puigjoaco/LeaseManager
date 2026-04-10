# Handoff Greenfield 2026-03-22

Este documento resume el estado actual del greenfield `LeaseManager` dentro de `D:/Proyectos/LeaseManager/Produccion 1.0` para retomar en otro thread sin perder contexto.

## 1. Contexto de repositorio

### Root activo nuevo

`D:/Proyectos/LeaseManager/Produccion 1.0`

### Root legacy read-only

`D:/Proyectos/LeaseManager`

Regla vigente:
- el root legacy se usa como fuente de lectura para reglas, schema, inventarios, integraciones, contexto contable, SII y Banco;
- no se copia el schema 1:1;
- no se copian secretos reales a archivos versionados;
- no se borra ni refactoriza el root legacy.

## 2. Stack y límites

Stack canónico activo:
- `Django 5`
- `Django REST Framework`
- `PostgreSQL`
- `Celery + Redis`
- `React + TypeScript + Vite`

Reglas de trabajo que se mantuvieron en toda la sesión:
- no rehacer scaffold;
- no commit todavía;
- no deploy todavía;
- no usar `git add .`;
- usar `apply_patch` para ediciones manuales;
- mantener modelo canónico nuevo, no lift-and-shift del legacy.

## 3. Backend implementado

### Plataforma base

Ya existían y se mantuvieron operativos:
- `users`
- `core`
- `audit`
- `health`

### Módulos implementados en el greenfield

Se implementaron y validaron:
- `patrimonio`
- `operacion`
- `contratos`
- `cobranza`
- `conciliacion`
- `contabilidad`
- `documentos`
- `canales`
- `sii`
- `reporting`
- `compliance`

## 4. Qué hace hoy el backend nuevo

### Patrimonio
- `Socio`, `Empresa`, `ComunidadPatrimonial`, `ParticipacionPatrimonial`, `Propiedad`
- ownership canónico y validaciones `100%`

### Operación
- `CuentaRecaudadora`
- `IdentidadDeEnvio`
- `MandatoOperacion`
- `AsignacionCanalOperacion`

### Contratos
- `Arrendatario`
- `Contrato`
- `ContratoPropiedad`
- `PeriodoContractual`
- `CodeudorSolidario`
- `AvisoTermino`

### Cobranza activa
- `ValorUFDiario`
- `PagoMensual`
- `AjusteContrato`
- `GarantiaContractual`
- `HistorialGarantia`
- `RepactacionDeuda`
- `CodigoCobroResidual`
- `EstadoCuentaArrendatario`

### Conciliación
- `ConexionBancaria`
- `MovimientoBancarioImportado`
- `IngresoDesconocido`
- match exacto a `PagoMensual`
- match exacto a `CodigoCobroResidual`
- `ManualResolution` para cargos o ingresos no asignables

### Contabilidad
- `RegimenTributarioEmpresa`
- `ConfiguracionFiscalEmpresa`
- `CuentaContable`
- `ReglaContable`
- `MatrizReglasContables`
- `EventoContable`
- `AsientoContable`
- `MovimientoAsiento`
- `PoliticaReversoContable`
- `ObligacionTributariaMensual`
- `LibroDiario`
- `LibroMayor`
- `BalanceComprobacion`
- `CierreMensualContable`

### Documentos
- `ExpedienteDocumental`
- `DocumentoEmitido`
- `PoliticaFirmaYNotaria`
- formalización bloqueada si faltan firmas/notaría según política

### Canales
- `CanalMensajeria`
- `MensajeSaliente`
- preparación de mensajes con resolución de identidad
- bloqueo con `ManualResolution` cuando falta gate, identidad o destinatario
- registro de envío manual controlado

### SII
- `CapacidadTributariaSII`
- `DTEEmitido`
- `F29PreparacionMensual`
- `ProcesoRentaAnual`
- `DDJJPreparacionAnual`
- `F22PreparacionAnual`
- DTE borrador desde pagos cobrados
- F29 desde cierre mensual aprobado + obligaciones
- DDJJ/F22 desde 12 cierres aprobados
- todo queda en modo borrador/controlado, no presentación final

### Reporting
- dashboard operativo
- resumen financiero mensual
- resumen por socio
- resumen de libros por período
- resumen tributario anual

### Compliance
- `PoliticaRetencionDatos`
- `ExportacionSensible`
- cifrado real con `cryptography`
- expiración máxima 30 días
- soporte de `hold_activo`
- acceso y revocación auditables

## 5. Decisiones importantes tomadas

### Legacy
- el legacy sí se usa como contexto y contraste;
- no se usa como blueprint directo del sistema nuevo.

### Cobranza vs SII
- `PagoMensual` ahora guarda:
  - `monto_facturable_clp`
  - `monto_calculado_clp`
- esto se hizo para separar el monto real a facturar del monto con código de conciliación embebido.

### SII
- `DTEEmision`, `F29Preparacion`, `DDJJPreparacion` y `F22Preparacion` se construyen desde datos internos del greenfield;
- no dependen de propuestas externas del SII;
- no se implementó presentación final crítica.

### Compliance
- los exportes sensibles no son solo links o hashes;
- se cifran realmente;
- expiran si no tienen hold.

## 6. Migración real desde legacy

### Ya existe pipeline de migración

Carpeta:
`D:/Proyectos/LeaseManager/Produccion 1.0/migration`

Archivos clave:
- `migration/readers.py`
- `migration/transformers.py`
- `migration/importers.py`
- `migration/scripts/export_legacy_seed_bundle.py`
- `migration/scripts/import_seed_bundle.py`

### Qué hace hoy

1. Lee la BD legacy en modo read-only.
2. Transforma a un bundle canónico.
3. Importa idempotentemente al sistema nuevo entidades determinísticas.

### Qué ya puede importar

Importa de forma segura:
- `Socio`
- `Empresa`
- `ComunidadPatrimonial`
- `ParticipacionPatrimonial`
- `Propiedad`
- `CuentaRecaudadora`
- `Arrendatario`

Además ya puede importar:
- `Contrato`
- `ContratoPropiedad`
- `PeriodoContractual`
- `AvisoTermino`

Pero solo cuando:
- ya existe una `Propiedad` canónica;
- ya existe un `Arrendatario` canónico;
- existe un `MandatoOperacion` activo y único para la propiedad;
- el candidato contractual viene con los campos mínimos requeridos.

### Qué sigue quedando fuera o en revisión

- importaciones que requieran inferencias ambiguas;
- casos sin mandato operativo único;
- agregados que en el mapping quedaron como `requiere_decision_manual`.

Si el contrato no es seguro de importar:
- no se inventa;
- queda en `skipped` con motivo explícito.

## 7. Validación realizada

### Backend

Se fue validando iterativamente durante toda la sesión con SQLite temporal.

Último estado verificado:
- `manage.py check` OK
- `manage.py makemigrations --check --dry-run` OK
- `manage.py test` OK

Conteo actual:
- `103` tests pasando

Incluye cobertura para:
- módulos de dominio
- conciliación
- ledger contable
- documental
- canales
- SII mensual y anual
- reporting
- compliance
- pipeline de migración

## 8. Limitación aún abierta

Sigue abierta la misma limitación estructural del greenfield:
- todavía no se validó el runtime real con `PostgreSQL + Redis` levantados vía Docker en este flujo;
- se siguió usando SQLite temporal para tooling y tests locales.

Esto significa:
- el backend está muy avanzado y consistente a nivel funcional;
- pero falta la validación real de infraestructura objetivo.

## 9. Dónde estamos

Estado actual:
- el backend greenfield está ampliamente construido;
- ya no estamos en fase de scaffold ni de modelado básico;
- ahora el trabajo tiene más sentido en:
  - validación runtime real;
  - corrida controlada del pipeline de migración contra la BD legacy;
  - completar integración real/operacional sobre lo ya modelado;
  - o empezar a montar frontend sobre la superficie ya existente.

## 10. Hacia dónde vamos

Siguiente paso recomendado de mayor valor práctico:

### Opción recomendada
- validar el backend con `PostgreSQL + Redis` reales;
- luego ejecutar un primer export/import controlado del bundle legacy contra la BD nueva;
- revisar qué entra limpio y qué queda en `skipped`.

### Después de eso
- ajustar importación real de contratos según `MandatoOperacion`;
- decidir si se amplía el pipeline hacia pagos/movimientos bancarios/documentos;
- o empezar frontend/backoffice sobre esta base.

## 11. Comandos útiles para retomar

### Validación backend
```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/backend"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

### Levantar infra local
```powershell
docker compose -f "D:/Proyectos/LeaseManager/Produccion 1.0/infra/docker-compose.yml" up -d
```

### Exportar bundle desde legacy
```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
$env:LEGACY_DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\export_legacy_seed_bundle.py
```

### Importar bundle al sistema nuevo
```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py migration\bundles\legacy_seed_bundle.json
```

## 12. Recordatorios críticos para el próximo thread

- seguir tratando `D:/Proyectos/LeaseManager` como legacy read-only;
- no copiar secretos reales al repo nuevo;
- no commit ni deploy todavía salvo instrucción explícita;
- no usar `git add .`;
- no asumir que el pipeline ya migró datos reales: hoy solo está implementado y validado localmente;
- si se va a correr una migración real, primero validar runtime con PostgreSQL/Redis del greenfield.

