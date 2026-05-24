# AGENTS.md

Guia operativa para trabajar dentro del root limpio de `LeaseManager`.

## Identidad del proyecto

Este root es el proyecto nuevo y activo de `LeaseManager`.

Regla base:

- Este repositorio contiene la codebase activa del greenfield.
- `D:/Proyectos/LeaseManager` es el root limpio activo despues del reemplazo
  de mayo 2026.
- La rama diaria debe ser `main`, sincronizada con `origin/main`.
- Worktrees hermanos con ramas `codex/...` son laboratorios tacticos por
  frente y deben usarse automaticamente para cambios no triviales o riesgosos.
- El root historico/sucio queda como savegame read-only para inventario,
  migracion, reglas de negocio, integraciones, certificados y contraste.
- No borrar ni reestructurar savegames o fuentes historicas salvo instruccion
  explicita del usuario y respaldo verificable.

## Fuente de verdad y precedencia

Primero leer `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`.

Si hay conflicto, aplicar este orden:

1. `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md` solo para estado de fuentes,
   jerarquia documental y estado de archivos historicos.
2. `01_Set_Vigente/PRD_CANONICO.md` como PRD vigente aceptado de mayo 2026.
3. `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`.
4. ADRs activos en `02_ADR_Activos/`.
5. `08_Auditoria_Stack/ADR_STACK_FINAL.md`.
6. `docs/architecture/ARQUITECTURA_MAESTRA_LEASEMANAGER.md`.
7. `docs/product/PLAN_EJECUCION_TRAZABLE_CIERRE_MAYO_2026.md`.
8. `docs/product/STAGE_CARDS/`.
9. `03_Ejecucion_Tecnica/`.
10. `04_Auditoria_y_Cierre/`.
11. `05_Contexto_Historico/`, `06_Fuentes_PRD_1_26/`,
    `07_ADR_Historicos_o_Podados/` solo como trazabilidad.

`docs/product/PRD_CANONICO_MAYO_2026_CANDIDATO.md` es solo trazabilidad de la
promocion ya ejecutada. No debe usarse como segunda fuente de producto.

## Stack obligatorio

Stack canonico del v1:

- Arquitectura: monolito modular.
- Backend: `Django 5`.
- API: `Django REST Framework`.
- Base de datos: `PostgreSQL`.
- Jobs/colas: `Celery + Redis`.
- Frontend: `React + TypeScript + Vite`.
- Documentos: `PDF` canonico.

No introducir como base del proyecto:

- `Next.js`.
- `Supabase` como modelo final del sistema.
- `Django Ninja`.
- `pgvector`.
- Microservicios.
- Capacidades IA fuera del boundary activo.

## Estructura del root

- `backend/`: API, auth, RBAC, auditoria, dominio y jobs.
- `frontend/`: backoffice web.
- `infra/`: infraestructura local y bootstrap.
- `migration/`: inventario legacy, extractores read-only, mapeos y decisiones
  de migracion.
- `docs/governance/`: fuente de verdad y protocolo operativo.
- `docs/architecture/`: arquitectura de producto sin herramientas ejecutoras.
- `docs/product/`: anexos, plan trazable, etapas, evidencia y bloqueos.
- `docs/operations/`: runbooks de operacion, cutover, backup y restore.

## Protocolo de trabajo

Aplicar `docs/governance/CODEX_OPERATING_PROTOCOL_MAYO_2026.md`.

Antes de abrir o continuar cualquier cambio no trivial, leer
`docs/product/EXECUTION_CURSOR_MAYO_2026.md` y confirmar el estado real con
`git status --short --branch` y `git worktree list`. El cursor no reemplaza al
PRD ni a las fuentes rectoras: solo fija el frente activo para evitar que
compactaciones, summaries o `goal_context` reabran metatareas ya cerradas.

Si existe un worktree tactico sucio, ese trabajo debe terminarse, pausarse en el
cursor o descartarse con instruccion segura antes de abrir otro frente de
producto. Un `goal_context`, objetivo persistente o conversacion anterior no
autoriza secretos, `.env`, bases reales, backfills, deploys ni integraciones.

Usar worktree hermano con rama `codex/...` automaticamente cuando el cambio
afecte:

- backend, modelos, migraciones, jobs, permisos, seguridad o auditoria;
- frontend amplio, navegacion, build o flujos de usuario;
- CI, scripts, gates, smoke tests o validadores;
- datos, migracion, inventarios, mapeos o backfills;
- contabilidad, SII, banco, WebPay, correo, UF o documentos;
- PRD, arquitectura, plan de ejecucion, fichas de etapa o reglas de gobierno.

Trabajar directo en `main` solo para inspeccion read-only o cambios minimos de
bajo riesgo solicitados explicitamente. Mantener `main` limpio.

## Orden de construccion

Seguir esta secuencia y no saltarla sin una razon fuerte:

1. `PlataformaBase`.
2. `Patrimonio`.
3. `Operacion`.
4. `Contratos`.
5. `CobranzaActiva`.
6. `Conciliacion`.
7. `Contabilidad`.
8. `Documentos`.
9. `Canales`.
10. `SII`.
11. `Reporting`.

Dependencias criticas:

- `Contabilidad` no parte antes de que `Conciliacion` genere hechos confiables.
- `SII` no parte antes de `ConfiguracionFiscalEmpresa`, ledger y cierre
  mensual.
- `Documentos` no cierra sin `PoliticaFirmaYNotaria`.
- `Reporting` no cierra si sus cifras no trazan a datos, ledger o documentos.

## Modelo canonico

Disenar contra el modelo de `LeaseManager`, no contra el schema legacy.

Entidades estructurales que deben existir en el sistema nuevo:

- `Socio`, `Empresa`, `ParticipacionPatrimonial`, `Propiedad`.
- `CuentaRecaudadora`, `MandatoOperacion`, `IdentidadDeEnvio`.
- `Arrendatario`, `CodeudorSolidario`, `Contrato`, `ContratoPropiedad`,
  `PeriodoContractual`, `AvisoTermino`.
- `PagoMensual`, `AjusteContrato`, `GarantiaContractual`,
  `HistorialGarantia`, `IngresoDesconocido`, `CodigoCobroResidual`.
- `RegimenTributarioEmpresa`, `ConfiguracionFiscalEmpresa`,
  `EventoContable`, `ReglaContable`, `MatrizReglasContables`,
  `AsientoContable`, `MovimientoAsiento`, `CierreMensualContable`,
  `ProcesoRentaAnual`.

Regla critica:

- No hacer lift-and-shift 1:1 desde Supabase legacy al modelo nuevo.

## Integraciones y gates

Todas las integraciones arrancan cerradas o condicionadas segun
`MATRIZ_GATES_EXTERNOS.md`.

Reglas:

- No conectar produccion por defecto.
- No usar credenciales reales en pruebas automaticas sin validacion explicita.
- No abrir `Email`, `WhatsApp`, `Banco`, `UF`, `SII`, `WebPay` ni storage
  hasta tener auditoria, permisos, trazabilidad, prueba aislada y rollback.
- Las capacidades `Podadas` no se implementan como compromiso activo del v1.

## Migracion desde LeaseManager historico

El root historico se usa solo para:

- inventario de secretos;
- inventario de activos sensibles;
- inventario de schema y migraciones;
- lectura de integraciones existentes;
- extraccion de datos y documentos.

Reglas de migracion:

- scripts de extraccion deben ser read-only;
- nunca guardar valores secretos en archivos versionados;
- certificados y credenciales se reprovisionan desde un manifiesto seguro
  externo;
- cada agregado migrado debe quedar como `migrable_directo`,
  `requiere_transformacion` o `requiere_decision_manual`.

## Seguridad y secretos

Reglas absolutas:

- No copiar claves reales a markdown, fixtures, tests ni commits.
- No imprimir secretos completos en terminal ni respuestas.
- No persistir `.env` reales en archivos versionados.
- No mover certificados productivos al repo nuevo.
- Usar referencias, nombres, owners, estados y entornos; no valores.

## Validacion minima

Antes de declarar listo un bloque base:

- backend levanta y pasa `manage.py check`;
- migraciones generan y aplican correctamente;
- healthcheck responde;
- auth minima funciona;
- frontend compila;
- inventarios de `migration/` se generan sin mutar el root historico;
- evidencia, bloqueos y trazabilidad quedan actualizados si el cambio afecta
  cierre de producto.

Comandos utiles:

### Backend

```powershell
cd backend
.\\.venv\\Scripts\\python.exe manage.py check
.\\.venv\\Scripts\\python.exe manage.py makemigrations
.\\.venv\\Scripts\\python.exe manage.py migrate
.\\.venv\\Scripts\\python.exe manage.py runserver
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
npm run build
```

### Infra

```powershell
docker compose -f "infra/docker-compose.yml" up -d
```

### Inventario legacy

```powershell
backend\\.venv\\Scripts\\python.exe migration\\scripts\\inventory_root_assets.py
```

## Estilo de trabajo

- Preferir cambios pequenos, verificables y modulares.
- Documentar decisiones nuevas en `docs/` cuando cambien arquitectura,
  migracion o boundaries.
- Mantener el proyecto nuevo desacoplado del tooling del root historico.
- Cuando un hallazgo historico contradiga el modelo nuevo, gana el set activo
  del root limpio.
- Registrar bloqueos en `docs/product/BLOCKERS_MAYO_2026.md`.
- Registrar evidencia en `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`.
- Actualizar `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` cuando cambie el
  estado de un frente.

## Que no hacer

- No portar pantallas legacy tal cual.
- No reusar el schema Supabase como modelo final.
- No implementar portales/IA/capacidades podadas solo porque existan en el
  legacy.
- No abrir gates por conveniencia.
- No usar el root historico/savegame como si fuera la nueva arquitectura.
- No declarar cierre de una etapa sin gate y evidencia.
