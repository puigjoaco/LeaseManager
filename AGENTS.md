# AGENTS.md

Guía operativa para trabajar dentro de `D:/Proyectos/LeaseManager/Produccion 1.0`.

## Identidad del proyecto

Este root es el proyecto **nuevo** de `LeaseManager`.

Regla base:
- `D:/Proyectos/LeaseManager/Produccion 1.0` es la codebase activa del greenfield.
- `D:/Proyectos/LeaseManager` es **legacy read-only** para inventario, migración, reglas de negocio, integraciones, certificados y contraste.
- No borrar, reestructurar ni “limpiar” el root legacy salvo instrucción explícita del usuario.

## Precedencia documental

Si hay conflicto, aplicar este orden:

1. `01_Set_Vigente/PRD_CANONICO.md`
2. `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`
3. ADRs activos en `02_ADR_Activos/`
4. `08_Auditoria_Stack/ADR_STACK_FINAL.md`
5. `03_Ejecucion_Tecnica/`
6. `04_Auditoria_y_Cierre/`
7. `05_Contexto_Historico/`, `06_Fuentes_PRD_1_26/`, `07_ADR_Historicos_o_Podados/` solo como trazabilidad

## Stack obligatorio

Stack canónico del v1:
- Arquitectura: monolito modular
- Backend: `Django 5`
- API: `Django REST Framework`
- Base de datos: `PostgreSQL`
- Jobs/colas: `Celery + Redis`
- Frontend: `React + TypeScript + Vite`
- Documentos: `PDF` canónico

No introducir como base del proyecto:
- `Next.js`
- `Supabase` como modelo final del sistema
- `Django Ninja`
- `pgvector`
- microservicios
- capacidades IA fuera del boundary activo

## Estructura del root

- `backend/`: API, auth, RBAC, auditoría, dominio y jobs
- `frontend/`: backoffice web
- `infra/`: infraestructura local y bootstrap
- `migration/`: inventario legacy, extractores read-only, mapeos y decisiones de migración
- `docs/`: runbooks, decisiones nuevas y documentación operativa del greenfield

## Orden de construcción

Seguir esta secuencia y no saltarla sin una razón fuerte:

1. `PlataformaBase`
2. `Patrimonio`
3. `Operacion`
4. `Contratos`
5. `CobranzaActiva`
6. `Conciliacion`
7. `Contabilidad`
8. `Documentos`
9. `Canales`
10. `SII`
11. `Reporting`

Dependencias críticas:
- `Contabilidad` no parte antes de que `Conciliacion` genere hechos confiables.
- `SII` no parte antes de `ConfiguracionFiscalEmpresa`, ledger y cierre mensual.
- `Documentos` no cierra sin `PoliticaFirmaYNotaria`.

## Modelo canónico

Diseñar contra el modelo de `LeaseManager`, no contra el schema legacy.

Entidades estructurales que deben existir en el sistema nuevo:
- `Socio`, `Empresa`, `ParticipacionPatrimonial`, `Propiedad`
- `CuentaRecaudadora`, `MandatoOperacion`, `IdentidadDeEnvio`
- `Arrendatario`, `CodeudorSolidario`, `Contrato`, `ContratoPropiedad`, `PeriodoContractual`, `AvisoTermino`
- `PagoMensual`, `AjusteContrato`, `GarantiaContractual`, `HistorialGarantia`, `IngresoDesconocido`, `CodigoCobroResidual`
- `RegimenTributarioEmpresa`, `ConfiguracionFiscalEmpresa`, `EventoContable`, `ReglaContable`, `MatrizReglasContables`, `AsientoContable`, `MovimientoAsiento`, `CierreMensualContable`, `ProcesoRentaAnual`

Regla crítica:
- No hacer lift-and-shift 1:1 desde Supabase legacy al modelo nuevo.

## Integraciones y gates

Todas las integraciones arrancan cerradas o condicionadas según `MATRIZ_GATES_EXTERNOS.md`.

Reglas:
- No conectar producción por defecto.
- No usar credenciales reales en pruebas automáticas sin validación explícita.
- No abrir `Email`, `WhatsApp`, `Banco`, `UF`, `SII` hasta tener auditoría, permisos, trazabilidad y prueba aislada satisfactoria.
- Las capacidades `Podadas` no se implementan como compromiso activo del v1.

## Migración desde LeaseManager legacy

El root legacy se usa solo para:
- inventario de secretos
- inventario de activos sensibles
- inventario de schema y migraciones
- lectura de integraciones existentes
- extracción de datos y documentos

Reglas de migración:
- scripts de extracción deben ser **read-only**
- nunca guardar valores secretos en archivos versionados
- certificados y credenciales se reprovisionan desde un manifiesto seguro externo
- cada agregado migrado debe quedar como:
  - `migrable_directo`
  - `requiere_transformacion`
  - `requiere_decision_manual`

## Seguridad y secretos

Reglas absolutas:
- No copiar claves reales a markdown, fixtures, tests ni commits.
- No imprimir secretos completos en terminal ni respuestas.
- No persistir `.env` reales en archivos versionados.
- No mover certificados productivos al repo nuevo.
- Usar referencias, nombres, owners, estados y entornos; no valores.

## Validación mínima

Antes de declarar listo un bloque base:
- backend levanta y pasa `manage.py check`
- migraciones generan y aplican correctamente
- healthcheck responde
- auth mínima funciona
- frontend compila
- inventarios de `migration/` se generan sin mutar el root legacy

Comandos útiles:

### Backend
```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/backend"
.\\.venv\\Scripts\\python.exe manage.py check
.\\.venv\\Scripts\\python.exe manage.py makemigrations
.\\.venv\\Scripts\\python.exe manage.py migrate
.\\.venv\\Scripts\\python.exe manage.py runserver
```

### Frontend
```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/frontend"
npm install
npm run dev
npm run build
```

### Infra
```powershell
docker compose -f "D:/Proyectos/LeaseManager/Produccion 1.0/infra/docker-compose.yml" up -d
```

### Inventario legacy
```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\\.venv\\Scripts\\python.exe migration\\scripts\\inventory_root_assets.py
```

## Estilo de trabajo

- Preferir cambios pequeños, verificables y modulares.
- Documentar decisiones nuevas en `docs/` cuando cambien arquitectura, migración o boundaries.
- Mantener el proyecto nuevo desacoplado del tooling del root legacy.
- Cuando un hallazgo del legacy contradiga el modelo nuevo, gana el set activo de `Produccion 1.0`.

## Qué no hacer

- No portar pantallas legacy “tal cual”.
- No reusar el schema Supabase como modelo final.
- No implementar portales/IA/capacidades podadas sólo porque existan en el legacy.
- No abrir gates por conveniencia.
- No usar el root actual como si fuera la nueva arquitectura.

