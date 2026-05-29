# Etapa 4 - SII y DTE

## Objetivo

Preparar facturacion y comunicacion tributaria sin emitir ni certificar contra
produccion por defecto.

## Alcance

- Configuracion fiscal por empresa.
- DTE 34 cuando corresponda.
- Estados y respuestas SII.
- Validacion de reglas tributarias.

## Gate

- Empresa emisora habilitada.
- Cada capacidad SII abierta, DTE y F29 debe pertenecer a una empresa con
  `ConfiguracionFiscalEmpresa` activa propia; el dominio/API rechaza nuevas
  escrituras que no cumplan esa regla.
- Una `ConfiguracionFiscalEmpresa` activa fuera del regimen fiscal
  automatizable v1 bloquea la apertura de capacidades SII y readiness de
  snapshots; no se automatiza tributacion oficial fuera de ese boundary.
- Cada artefacto tributario debe usar la capacidad SII exacta de su flujo:
  DTE con `DTEEmision`, consulta de estado DTE con `DTEConsultaEstado`, F29
  con `F29Preparacion`, DDJJ con `DDJJPreparacion` y F22 con
  `F22Preparacion`; la readiness debe bloquear snapshots heredados con
  capacidad de otra familia aunque sea de la misma empresa.
- Comunidades y personas naturales tratadas segun regla validada.
- Certificado/ambiente aislado autorizado.
- Regla fiscal respaldada por SII, normativa o experto.

## Preparacion local segura

- Las capacidades SII abiertas deben registrar refs trazables y no sensibles de
  certificado, evidencia, prueba de flujo, autorizacion de ambiente y regla
  fiscal cuando aplica, y no pueden sustituir la configuracion fiscal activa de
  otra empresa.
- DTE, F29, DDJJ/F22 y procesos anuales solo aceptan refs tributarias no
  sensibles para tracking, borradores y paquetes; las APIs y snapshots redactan
  refs o payloads sensibles heredados antes de exponerlos al backoffice.
- Los payloads tributarios locales (`ultimo_resultado`, `resumen_formulario`,
  `resumen_anual`, `resumen_paquete`, `resumen_f22`) rechazan URLs, tokens,
  credenciales, correos y claves sensibles como `api_key`, `access_token` o
  `credential`; readiness Etapa 4 detecta snapshots heredados sin exponer esos
  valores.
- Las observaciones tributarias de DTE, F29, DDJJ y F22 deben ser no
  sensibles: dominio y servicios rechazan nuevas URLs, correos, tokens o
  credenciales; API, snapshot y admin Django redactan observaciones heredadas;
  readiness Etapa 4 las clasifica sin exponer el valor.
- El admin Django de SII mantiene cerrada la superficie administrativa:
  `CapacidadTributariaSIIAdmin`, `DTEEmitidoAdmin`,
  `F29PreparacionMensualAdmin`, `ProcesoRentaAnualAdmin`,
  `DDJJPreparacionAnualAdmin` y `F22PreparacionAnualAdmin` muestran versiones
  redactadas de refs, payloads y observaciones sensibles heredadas, no buscan
  por campos crudos como `certificado_ref`, `evidencia_ref`,
  `sii_track_id`, `borrador_ref` o `paquete_ref`, muestran sus campos en solo
  lectura, bloquean borrado manual y mantienen el alta manual deshabilitada
  desde backoffice.
- DTE, F29, DDJJ/F22 y procesos anuales rechazan por dominio nuevas escrituras
  asociadas a empresas sin `ConfiguracionFiscalEmpresa` activa propia.
- Los eventos de auditoria de cambios de estado DTE registran `sii_track_id`
  redactado si existe una referencia sensible heredada.
- Los borradores DTE/F29/anuales y los cambios de estado externo revalidan el
  gate antes de avanzar. Los DTE marcados `enviado_manual_controlado`
  revalidan `DTEEmision`; los estados finales `aceptado`, `rechazado` o
  `anulado` revalidan `DTEConsultaEstado` abierta y lista.
- F29, DDJJ y F22 en estado preparado, aprobado, observado o rectificado deben
  mantener una capacidad SII abierta y lista; el readiness bloquea artefactos
  heredados avanzados con capacidad condicionada, cerrada o invalida.
- `F29Presentacion` y `PresentacionAnualFinal` no se registran desde el flujo
  local sin gate propio o reemision formal del set.
- `audit_stage4_sii_readiness` consolida configuracion fiscal por empresa,
  capacidades SII, DTE, F29 y preparacion anual sin conectar SII ni leer
  certificados, y reporta refs, payloads u observaciones sensibles existentes
  sin imprimir sus valores.
- `audit_stage4_sii_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre SII.
- Una fuente evidencial debe incluir `--source-label` y
  `--authorization-ref` no sensibles. Sin esas refs, el tipo de fuente queda
  reconocido pero no puede cerrar Etapa 4.
- `scripts/run-stage4-readiness-gate.ps1` ejecuta el diagnostico local con
  SQLite efimero bajo `local-evidence/`, no conecta SII, no lee `.env`, no usa
  certificados y reserva `-RequireReady` para fuentes autorizadas con refs
  trazables de ledger, ambiente, regla fiscal y responsable.

```powershell
scripts\run-stage4-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

SII no cierra con mocks. Requiere evidencia de ambiente autorizado y regla
fiscal validada.
