# PRD Canonico - LeaseManager

Estado: vigente  
Fecha de emision: 15/03/2026  
Audiencia: producto, arquitectura, desarrollo y operaciones  
Sustituye funcionalmente a: [PRD_MAESTRO_DEFINITIVO.md](./PRD_MAESTRO_DEFINITIVO.md)

## 1. Estatus y jerarquia documental

Este documento es la unica fuente vigente de producto para LeaseManager. Define la mision, el boundary, el modelo de dominio, las reglas canonicamente activas, los flujos obligatorios, los requisitos no funcionales y la aceptacion minima para construir el sistema.

Artefactos complementarios obligatorios:

- [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md): decide si una capacidad externa esta activa, suspendida o degradada.
- [ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md](./ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md), [ADR_ARQUITECTURA_002_IDENTIDAD_ENVIO.md](./ADR_ARQUITECTURA_002_IDENTIDAD_ENVIO.md), [ADR_ARQUITECTURA_003_CAPACIDADES_SII.md](./ADR_ARQUITECTURA_003_CAPACIDADES_SII.md), [ADR_ARQUITECTURA_004_ESTRATEGIA_API.md](./ADR_ARQUITECTURA_004_ESTRATEGIA_API.md), [ADR_ARQUITECTURA_005_ESTRATEGIA_DOCUMENTAL.md](./ADR_ARQUITECTURA_005_ESTRATEGIA_DOCUMENTAL.md), [ADR_ARQUITECTURA_006_SECRETOS_Y_AUDITORIA.md](./ADR_ARQUITECTURA_006_SECRETOS_Y_AUDITORIA.md) y [ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md](./ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md): fijan implementacion donde el PRD delega.
- [BACKLOG_INVESTIGACION.md](./BACKLOG_INVESTIGACION.md): concentra solo expansiones futuras fuera del boundary activo.
- [AUDITORIA_MAXIMA_PRD_MAESTRO.md](./AUDITORIA_MAXIMA_PRD_MAESTRO.md): explica por que este PRD reemplaza funcionalmente al maestro anterior.
- [AUDITORIA_AUTOSUFICIENCIA_SET_ACTIVO.md](./AUDITORIA_AUTOSUFICIENCIA_SET_ACTIVO.md): registra el cierre del set activo como sistema documental autosuficiente.

Precedencia:

1. Este PRD manda sobre objetivos, dominio, reglas y acceptance.
2. La matriz de gates manda sobre activacion real de integraciones y automatizaciones externas.
3. Los ADR mandan sobre decisiones tecnicas expresamente delegadas por este PRD.
4. El backlog registra incertidumbre; no invalida reglas ya cerradas.
5. Los documentos historicos no son normativos.

Si hay conflicto:

- una regla de dominio de este PRD prevalece sobre un ejemplo, roadmap o artefacto historico;
- un gate cerrado prevalece sobre una ambicion de roadmap;
- un ADR no puede cambiar el dominio sin reemitir este PRD.

## 2. Mision, boundary y segmentacion

### 2.1 Mision del producto

LeaseManager es una plataforma de administracion de arriendos comerciales en Chile. Su objetivo es centralizar el ciclo operacional completo de cada arriendo en un sistema auditable, trazable y operable en modo normal o degradado sin destruir la coherencia juridica, financiera ni documental del negocio.

Capacidades objetivo del v1 canonico:

- datos maestros patrimoniales y operativos;
- onboarding de arrendatarios;
- contratos y periodos contractuales;
- calculo mensual de renta en CLP con UF y codigo de conciliacion efectivo;
- notificaciones por email y WhatsApp cuando el gate del canal este abierto;
- conciliacion bancaria exacta, asistida o manual;
- contabilidad nativa basada en ledger y asientos balanceados;
- cierre mensual contable y tributario dentro del sistema;
- garantias, deuda, repactacion y cobranza post-contrato;
- expediente documental contractual;
- emision tributaria y preparacion mensual/anual solo para capacidades SII cuyo gate este abierto;
- dashboards, reportes y auditoria operacional.

### 2.2 Boundary de LeaseManager v1

LeaseManager v1 se orienta a:

- arriendos comerciales en Chile;
- operacion mensual en `CLP` y `UF`;
- propiedades individuales o parejas `principal + vinculada`;
- operacion administrada por un actor humano responsable;
- integraciones oficiales o defensibles.

Fuera del boundary activo del v1:

- scraping bancario;
- cambio de arrendatario dentro del mismo contrato;
- contratos multi-propiedad abiertos;
- automatizacion tributaria autonoma de alta criticidad;
- automatizacion de portales inmobiliarios;
- IA semantica, conversacional o clasificatoria como capacidad activa del v1;
- cualquier regimen tributario distinto del expresamente soportado por este PRD.

### 2.3 Politicas de producto v1

Estas politicas son decisiones de producto del v1. No se declaran como ley universal del dominio y podran revisarse solo mediante una nueva emision del PRD:

- contratos mensuales que inician dia `1` y terminan ultimo dia del mes;
- `dia_pago_mensual` entre `1` y `5`;
- una propiedad activa se cobra en una sola `CuentaRecaudadora`;
- una vinculacion oficial admite solo `1 principal + 1 vinculada`;
- `CLP 1.000` como monto minimo de contrato, tramo o ajuste resultante.

### 2.4 Localizacion operativa

- idioma de producto: espanol de Chile;
- formato de fecha: `dd/mm/yyyy`;
- zona horaria operativa: `America/Santiago`;
- monedas operativas: `CLP` y `UF`.

### 2.5 Indicadores de exito iniciales

| Indicador | Fuente y formula | Owner y periodicidad | Target inicial |
|---|---|---|---|
| `TiempoAdministrativoMensual` | horas operativas mensuales / cartera comparable, medida contra baseline pre-implementacion | `AdministradorGlobal`, mensual | `-90%` en 6 meses |
| `ErrorPostConciliacion` | pagos conciliados que requirieron correccion posterior / pagos conciliados del periodo | `AdministradorGlobal`, mensual | `<1%` |
| `PagoPuntual` | pagos en fecha / pagos exigibles del periodo frente a baseline historico de la cartera | `AdministradorGlobal`, mensual | `+15%` |
| `DashboardP95` | percentil 95 de carga del dashboard principal con cache habilitada | `AdministradorGlobal`, semanal | `<2s` |
| `DocumentoContractualP95` | percentil 95 de generacion del PDF contractual | `AdministradorGlobal`, semanal | `<3s` |
| `UptimeMensual` | disponibilidad mensual medida sobre servicios criticos definidos | `AdministradorGlobal`, mensual | `99.5%` |
| `AdopcionFlujoDocumental` | contratos nuevos emitidos por flujo canonico / contratos nuevos del periodo | `AdministradorGlobal`, mensual | `>95%` |

## 3. Actores y modelo operativo

### 3.1 Roles base

| Rol | Alcance | Restricciones duras |
|---|---|---|
| `AdministradorGlobal` | configura sistema, aprueba cierres, controla integraciones, resuelve excepciones y administra usuarios | ninguna capacidad operativa supera este rol |
| `OperadorDeCartera` | ejecuta alta de datos, contratos, cobros, documentos y seguimiento diario | no gestiona secretos ni politicas globales salvo delegacion explicita |
| `Socio` | consulta cartera, participaciones, resultados y documentos filtrados | no opera contratos ni conciliaciones |

Regla de RBAC:

- pueden existir roles adicionales;
- todo rol adicional deriva por minimo privilegio;
- ningun rol custom supera a `AdministradorGlobal`.
- el rol custom recomendado para revision externa es `RevisorFiscalExterno`, siempre read-only y nunca bloqueante para el flujo base.

### 3.2 Actores operativos canonicamente separados

| Actor operativo | Definicion canonica |
|---|---|
| `Propietario` | persona o entidad titular del activo o del derecho economico principal |
| `AdministradorOperativo` | actor responsable del ciclo operacional del arriendo en la plataforma |
| `Recaudador` | actor al que pertenece la `CuentaRecaudadora` y que recibe operativamente el flujo bancario |
| `EntidadFacturadora` | actor habilitado para emitir documentos tributarios cuando el gate SII de la capacidad aplicable esta abierto |
| `CuentaRecaudadora` | cuenta o instrumento de recaudacion asociado al cobro operativo |
| `IdentidadDeEnvio` | identidad autenticada de salida para email o WhatsApp |
| `MandatoOperacion` | relacion vigente que une activo, responsable operacional, recaudacion, facturacion y canales autorizados |

Regla clave:

- LeaseManager no deduce automaticamente que quien recauda es quien factura o quien comunica. Esa relacion debe estar declarada en un `MandatoOperacion`.

### 3.3 Permisos y aprobaciones criticas

| Accion critica | Ejecuta | Aprueba | Restriccion |
|---|---|---|---|
| `ReaperturaDeMes` | `AdministradorGlobal` | no aplica | siempre requiere justificacion auditable |
| `CierreMensualContableYTributario` | sistema u `OperadorDeCartera` preparan | `AdministradorGlobal` | solo se consolida si no quedan eventos pendientes ni descuadres |
| `AsignacionManualPagoAmbiguo` | `OperadorDeCartera` o `AdministradorGlobal` | `AdministradorGlobal` | nunca se consolida sin aprobacion final |
| `CambioDeGateSII` para `F29Presentacion`, `DDJJPreparacion`, `F22Preparacion` o `PresentacionAnualFinal` | `AdministradorGlobal` | no aplica | requiere evidencia del gate y checklist de readiness |
| `CambioDeGateComplianceDatos2026` | `AdministradorGlobal` | no aplica | requiere checklist legal-operativa completa y evidencia archivada |
| `SalidaTributariaMensualFinal` | sistema solo genera borrador | `AdministradorGlobal` | no existe envio autonomo por defecto |
| `SalidaTributariaAnualFinal` | sistema solo genera borrador | `AdministradorGlobal` | no existe envio autonomo por defecto |
| `ExportacionMasivaDeDatosSensibles` | `AdministradorGlobal` | no aplica | debe quedar `EventoAuditable` con motivo y scope |

Reglas:

- `RevisorFiscalExterno`, cuando se configure, solo observa, comenta y exporta dentro de su scope;
- `Socio` solo exporta informacion filtrada de su scope;
- los permisos efectivos se aplican sobre rol y scope operativo simultaneamente.

## 4. Bounded contexts y definiciones canonicas

### 4.1 Patrimonio

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `Socio` | `id`, `nombre`, `rut`, `email`, `telefono`, `domicilio`, `activo` | no puede eliminarse con participaciones activas |
| `Empresa` | `id`, `razon_social`, `rut`, `domicilio`, `giro`, `codigo_actividad_sii`, `estado` | si opera en plataforma debe tener participacion total `100%` y al menos un `MandatoOperacion` valido para activos administrados |
| `ParticipacionPatrimonial` | `id`, `owner_tipo`, `owner_id`, `participante_socio_id`, `participante_empresa_id`, `porcentaje`, `vigente_desde`, `vigente_hasta`, `activo` | la suma activa por entidad debe ser exactamente `100%`; una empresa owner solo admite participantes `Socio`; una comunidad admite participantes `Socio` o `Empresa` |
| `RepresentacionComunidad` | `id`, `comunidad_id`, `modo_representacion`, `socio_representante_id`, `vigente_desde`, `vigente_hasta`, `activo` | una comunidad activa debe tener exactamente una representacion activa vigente |
| `Propiedad` | `id`, `rol_avaluo`, `direccion`, `comuna`, `region`, `tipo_inmueble`, `owner_tipo`, `owner_id`, `codigo_propiedad`, `estado` | no puede pertenecer simultaneamente a empresa, comunidad y socio; `codigo_propiedad` es operacional y unico dentro de la `CuentaRecaudadora` activa |

Reglas adicionales:

- si la propiedad pertenece a comunidad, debe existir `RepresentacionComunidad` activa;
- una comunidad patrimonial puede ser solo de socios o mixta con socios y empresas;
- `codigo_propiedad` usa rango `001-999` por `CuentaRecaudadora`;
- una `CuentaRecaudadora` soporta como maximo `999` propiedades activas que usen conciliacion por monto embebido.

### 4.2 Operacion

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `MandatoOperacion` | `id`, `propiedad_o_pareja_id`, `propietario_ref`, `administrador_operativo_ref`, `recaudador_ref`, `entidad_facturadora_ref`, `cuenta_recaudadora_id`, `tipo_relacion_operativa`, `autoriza_recaudacion`, `autoriza_facturacion`, `autoriza_comunicacion`, `vigencia_desde`, `vigencia_hasta`, `estado` | debe existir antes de activar un contrato; fija quien recauda, quien comunica y quien factura |
| `CuentaRecaudadora` | `id`, `institucion`, `numero_cuenta`, `tipo_cuenta`, `titular_nombre`, `titular_rut`, `moneda_operativa`, `estado_operativo` | puede tener varias conexiones proveedoras, pero una sola conexion primaria activa por capacidad automatica |
| `IdentidadDeEnvio` | `id`, `canal`, `owner_tipo`, `owner_id`, `remitente_visible`, `direccion_o_numero`, `credencial_ref`, `estado` | las credenciales pertenecen al owner de la identidad, nunca a la cuenta bancaria |
| `AsignacionCanalOperacion` | `id`, `mandato_operacion_id`, `canal`, `identidad_envio_id`, `prioridad`, `estado` | resuelve la identidad por defecto por canal dentro del mandato |

Reglas adicionales:

- un contrato puede tener override explicito de `IdentidadDeEnvio`; si no existe, usa la asignacion del `MandatoOperacion`;
- si un canal no tiene identidad activa, el sistema no inventa un remitente sustituto.
- para boundary contable-tributario activo, `EntidadFacturadora` debe ser una `Empresa` con `ConfiguracionFiscalEmpresa` activa;
- si `Propietario`, `AdministradorOperativo`, `Recaudador` y `EntidadFacturadora` no coinciden, el `MandatoOperacion` debe declarar explicitamente la autorizacion de recaudar, facturar y comunicar;
- `CuentaRecaudadora` debe pertenecer exactamente al `Recaudador` declarado por el `MandatoOperacion`;
- si el `Propietario` es una comunidad y no tiene participantes empresa activos, `EntidadFacturadora` debe ser `null`;
- la identidad de envio de documentos contractuales o tributarios debe pertenecer a `EntidadFacturadora` o a `AdministradorOperativo` expresamente autorizado.

### 4.3 Contratos

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `Arrendatario` | `id`, `tipo_arrendatario`, `email`, `telefono`, `domicilio_notificaciones`, `estado_contacto`, `whatsapp_bloqueado` | puede ser persona natural o empresa; consolida `score_pago` en su estado de cuenta |
| `CodeudorSolidario` | `id`, `contrato_id`, `snapshot_identidad`, `fecha_inclusion`, `estado` | maximo `3` por contrato; opera por snapshot inmutable |
| `Contrato` | `id`, `codigo_contrato`, `mandato_operacion_id`, `arrendatario_id`, `fecha_inicio`, `fecha_fin_vigente`, `fecha_entrega`, `dia_pago_mensual`, `plazo_notificacion_termino_dias`, `dias_prealerta_admin`, `estado`, `tiene_tramos`, `tiene_gastos_comunes`, `snapshot_representante_legal` | identidad inmutable; si cambia el arrendatario nace un contrato nuevo |
| `ContratoPropiedad` | `id`, `contrato_id`, `propiedad_id`, `rol_en_contrato`, `porcentaje_distribucion_interna`, `codigo_conciliacion_efectivo_snapshot` | un contrato cubre `1` propiedad o `1` pareja `principal + vinculada` |
| `PeriodoContractual` | `id`, `contrato_id`, `numero_periodo`, `fecha_inicio`, `fecha_fin`, `monto_base`, `moneda_base`, `tipo_periodo`, `origen_periodo` | renovaciones y extensiones agregan periodos; no duplican contrato |
| `AvisoTermino` | `id`, `contrato_id`, `fecha_efectiva`, `causal`, `estado`, `registrado_por` | habilita contrato futuro y bloquea renovacion automatica mientras este vigente |

Reglas adicionales:

- una propiedad puede tener `1` contrato vigente y `1` contrato futuro;
- una propiedad vinculada no puede tener contrato activo independiente;
- `rol_en_contrato` solo admite `Principal` o `Vinculada`;
- la pareja `principal + vinculada` debe compartir arrendatario, calendario, garantia, aviso de termino y mandato operativo.
- un contrato futuro solo puede existir si hay `AvisoTermino` vigente o terminacion anticipada ejecutada;
- los contratos retroactivos son validos solo si no reconstruyen operaciones ficticias de meses ya cerrados;
- si un contrato retroactivo se registra despues del dia `5` del mes operativo, el sistema debe advertir posible necesidad de notificacion manual.

### 4.4 Cobranza

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `PagoMensual` | `id`, `contrato_id`, `periodo_contractual_id`, `mes`, `anio`, `monto_calculado_clp`, `monto_pagado_clp`, `fecha_vencimiento`, `fecha_deposito_banco`, `fecha_deteccion_sistema`, `estado_pago`, `dias_mora`, `codigo_conciliacion_efectivo` | existe uno por contrato por mes operativo |
| `DistribucionCobroMensual` | `id`, `pago_mensual_id`, `beneficiario_tipo`, `beneficiario_id`, `porcentaje_snapshot`, `monto_devengado_clp`, `monto_conciliado_clp`, `monto_facturable_clp`, `requiere_dte` | representa la atribucion economica del cobro mensual; no reemplaza al pago total |
| `AjusteContrato` | `id`, `contrato_id`, `tipo_ajuste`, `monto`, `moneda`, `mes_inicio`, `mes_fin`, `justificacion` | se aplica antes de insertar el codigo efectivo |
| `GarantiaContractual` | `id`, `contrato_id`, `monto_pactado`, `monto_recibido`, `monto_devuelto`, `estado_garantia`, `fecha_recepcion`, `fecha_cierre` | pertenece al contrato, no a la propiedad individual |
| `HistorialGarantia` | `id`, `contrato_id`, `tipo_movimiento`, `monto_clp`, `fecha`, `justificacion`, `movimiento_origen_id` | soporta deposito, devolucion y retencion parcial o total |
| `RepactacionDeuda` | `id`, `arrendatario_id`, `contrato_origen_id`, `deuda_total_original`, `cantidad_cuotas`, `monto_cuota`, `saldo_pendiente`, `estado` | no reescribe la historia del contrato origen |
| `IngresoDesconocido` | `id`, `cuenta_recaudadora_id`, `monto`, `fecha_movimiento`, `descripcion_origen`, `estado`, `sugerencia_asistida` | el sistema no lo asigna automaticamente a un contrato ambiguo |
| `CodigoCobroResidual` | `id`, `referencia_visible`, `arrendatario_id`, `contrato_origen_id`, `saldo_actual`, `estado`, `fecha_activacion` | reemplaza el viejo esquema `900-999`; nunca reutiliza el namespace de propiedades |
| `EstadoCuentaArrendatario` | `id`, `arrendatario_id`, `resumen_operativo`, `score_pago`, `observaciones` | consolida deuda, repactaciones y cumplimiento |

Reglas adicionales:

- `PagoMensual` representa siempre el cobro total del contrato;
- `DistribucionCobroMensual` representa la atribucion economica y facturable derivada de ese cobro;
- `estado_pago` admite al menos `Pendiente`, `Pagado`, `Atrasado`, `EnRepactacion`, `PagadoViaRepactacion`, `PagadoPorAcuerdoDeTermino` y `Condonado`;
- `fecha_deposito_banco` representa la fecha reportada por el provider cuando existe y es confiable;
- `fecha_deteccion_sistema` representa cuando LeaseManager conocio el movimiento;
- `dias_mora` y puntualidad usan `fecha_deposito_banco` cuando sea confiable; la auditoria operacional usa `fecha_deteccion_sistema`;
- `CodigoCobroResidual.referencia_visible` usa formato canonico `CCR-XXXXXX`, con `X` en base32 mayuscula sin caracteres ambiguos;
- el cobro residual no reemplaza ultimos tres digitos del monto;
- si el provider bancario expone referencia o descripcion confiable, el sistema puede hacer match exacto por `CodigoCobroResidual`;
- si el provider no expone referencia confiable, la conciliacion de deuda residual opera en modo asistido o manual.
- un pago repactado cuenta como cumplido para score solo si la cuota exigible del mes fue cubierta en plazo.

### 4.5 Contabilidad

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `RegimenTributarioEmpresa` | `codigo_regimen`, `descripcion`, `estado` | en v1 el unico regimen automatizable es `EmpresaContabilidadCompletaV1` |
| `ConfiguracionFiscalEmpresa` | `empresa_id`, `regimen_tributario`, `afecta_iva_arriendo`, `tasa_iva`, `aplica_ppm`, `ddjj_habilitadas`, `inicio_ejercicio`, `moneda_funcional`, `estado` | habilita contabilidad oficial, cierre mensual y preparacion anual solo si esta completa |
| `EventoContable` | `id`, `evento_tipo`, `entidad_origen_tipo`, `entidad_origen_id`, `fecha_operativa`, `moneda`, `monto_base`, `payload_resumen`, `idempotency_key`, `estado_contable` | nace desde hechos economicos confirmados; no se duplica para el mismo hecho |
| `ReglaContable` | `id`, `evento_tipo`, `plan_cuentas_version`, `criterio_cargo`, `criterio_abono`, `vigencia_desde`, `vigencia_hasta`, `estado` | traduce un `EventoContable` a asiento segun policy contable vigente |
| `MatrizReglasContables` | `id`, `plan_cuentas_version`, `evento_tipo`, `cuenta_debe`, `cuenta_haber`, `condicion_impuesto`, `estado` | version canonica del mapping evento -> cuentas |
| `CuentaContable` | `id`, `codigo`, `nombre`, `naturaleza`, `nivel`, `padre_id`, `estado` | pertenece al plan de cuentas activo |
| `AsientoContable` | `id`, `evento_contable_id`, `fecha_contable`, `periodo_contable`, `estado`, `debe_total`, `haber_total`, `moneda_funcional`, `hash_integridad` | debe cuadrar siempre `debe = haber`; no se edita en periodos cerrados |
| `MovimientoAsiento` | `id`, `asiento_contable_id`, `cuenta_contable_id`, `tipo_movimiento`, `monto`, `glosa`, `centro_resultado_ref` | representa el detalle cargo o abono |
| `PoliticaReversoContable` | `id`, `tipo_ajuste`, `usa_reverso`, `usa_asiento_complementario`, `permite_reapertura`, `aprobacion_requerida`, `ventana_operativa`, `estado` | define como se corrigen hechos posteriores al cierre |
| `CierreMensualContable` | `id`, `empresa_id`, `anio`, `mes`, `estado`, `fecha_preparacion`, `fecha_aprobacion`, `resumen_obligaciones` | bloquea nuevas mutaciones estructurales del periodo una vez aprobado |
| `ObligacionTributariaMensual` | `id`, `empresa_id`, `anio`, `mes`, `obligacion_tipo`, `base_imponible`, `monto_calculado`, `estado_preparacion` | alimenta `F29Preparacion` y otras salidas mensuales |
| `EstadoPreparacionTributaria` | `codigo`, `descripcion` | valores minimos: `NoAplica`, `PendienteDatos`, `EnPreparacion`, `Preparado`, `AprobadoParaPresentacion`, `Presentado`, `Observado`, `Rectificado` |
| `ProcesoRentaAnual` | `id`, `empresa_id`, `anio_tributario`, `estado`, `fecha_preparacion`, `resumen_anual`, `paquete_ddjj_ref`, `borrador_f22_ref` | consolida el cierre anual y la preparacion de renta |
| `LibroDiario` | `id`, `empresa_id`, `periodo`, `estado_snapshot`, `storage_ref` | vista derivada del ledger para el periodo |
| `LibroMayor` | `id`, `empresa_id`, `periodo`, `estado_snapshot`, `storage_ref` | vista derivada del ledger por cuenta |
| `BalanceComprobacion` | `id`, `empresa_id`, `periodo`, `estado_snapshot`, `storage_ref` | vista derivada para control de saldos y cierre |

Reglas adicionales:

- toda conciliacion bancaria confirmada genera `EventoContable`;
- toda emision tributaria confirmada genera `EventoContable`;
- toda recepcion, devolucion o retencion de garantia genera `EventoContable`;
- toda repactacion, ajuste o acuerdo de termino con efecto economico genera `EventoContable`;
- el `MotorContable` transforma `EventoContable` en `AsientoContable` usando `ReglaContable`;
- si un evento no puede contabilizarse automaticamente, queda `PendienteRevisionContable` y no desaparece silenciosamente;
- un `AsientoContable` cerrado no se edita; cualquier correccion posterior opera por reverso o asiento complementario auditable.
- el boundary tributario activo del v1 soporta solo `RegimenTributarioEmpresa = EmpresaContabilidadCompletaV1`;
- si la empresa no tiene `ConfiguracionFiscalEmpresa` completa, LeaseManager puede operar la capa contractual y de cobranza, pero bloquea cierre tributario automatizado;
- `F29Preparacion` consume solo obligaciones permitidas por `ConfiguracionFiscalEmpresa`;
- `DDJJPreparacion` y `F22Preparacion` solo derivan obligaciones expresamente habilitadas en `ConfiguracionFiscalEmpresa.ddjj_habilitadas`.
- el borrador `F29Preparacion` se construye desde el ledger interno de LeaseManager y no depende de una propuesta automatica transferida por SII.

### 4.6 Documentos

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `ExpedienteDocumental` | `id`, `entidad_tipo`, `entidad_id`, `estado`, `owner_operativo` | agrupa todo el historial documental de una entidad operativa |
| `DocumentoEmitido` | `id`, `expediente_id`, `tipo_documental`, `version_plantilla`, `checksum`, `fecha_carga`, `usuario`, `origen`, `estado`, `storage_ref` | cada documento critico debe quedar versionado y trazable |
| `PoliticaFirmaYNotaria` | `id`, `tipo_documental`, `requiere_firma_arrendador`, `requiere_firma_arrendatario`, `requiere_codeudor`, `requiere_notaria`, `modo_firma_permitido`, `estado` | define el grado de formalizacion exigido por documento |

Tipos documentales minimos:

- contrato principal;
- anexos;
- cartas de aviso;
- liquidaciones de garantia;
- respaldos tributarios;
- comprobantes notariales;
- consentimientos y evidencia de resolucion manual cuando aplique.

Reglas adicionales:

- el `ContratoPrincipal` requiere firma de arrendador y arrendatario;
- cuando el contrato incluya `CodeudorSolidario`, la politica documental define si firma obligatoriamente;
- la notaria no es regla universal del dominio; solo aplica cuando `PoliticaFirmaYNotaria.requiere_notaria = true`;
- un documento no puede quedar `Formalizado` si su politica exige notaria y no existe comprobante archivado.

### 4.7 Integraciones

| Entidad conceptual | Campos minimos | Reglas canonicas |
|---|---|---|
| `ProviderBancario` | `provider_key`, `capacidades`, `estado_catalogo` | define la interfaz de movimientos, saldos y conectividad |
| `ConexionBancaria` | `id`, `cuenta_recaudadora_id`, `provider_key`, `credencial_ref`, `scope`, `expira_en`, `estado_conexion`, `ultimo_exito_at`, `ultimo_error_at` | un provider se activa solo con gate abierto |
| `FuenteUF` | `source_key`, `prioridad`, `estado`, `ultimo_exito_at` | la cadena activa es `BancoCentral -> CMF -> MiIndicador -> carga manual auditada` |
| `CapacidadTributariaSII` | `id`, `empresa_id`, `capacidad_key`, `certificado_ref`, `ambiente`, `estado_gate`, `ultimo_resultado` | el set activo del v1 soporta `DTEEmision`, `DTEConsultaEstado`, `F29Preparacion`, `F29Presentacion`, `DDJJPreparacion` y `F22Preparacion` |
| `CanalMensajeria` | `canal`, `provider_key`, `estado_gate`, `restricciones_operativas` | email y WhatsApp se activan por gate separado |

### 4.8 Seguridad y auditoria

| Entidad | Campos minimos | Reglas canonicas |
|---|---|---|
| `EventoAuditable` | `id`, `actor`, `timestamp`, `entidad_tipo`, `entidad_id`, `accion`, `payload_hash`, `motivo`, `aprobacion_ref`, `external_ref` | toda accion sensible genera evento auditable |
| `ResolucionManual` | `id`, `motivo`, `usuario_responsable`, `datos_afectados`, `criterio_aplicado`, `evidencia_ref`, `resultado`, `fecha` | no hay resolucion manual invisible |
| `PoliticaRetencionDatos` | `id`, `categoria_dato`, `evento_inicio`, `plazo_minimo_anos`, `permite_borrado_logico`, `permite_purga_fisica`, `requiere_hold`, `estado` | define retencion, hold y exportacion de datos sensibles |
| `GateExterno` | `id`, `capacidad`, `provider_key`, `estado`, `entrada_cumplida`, `suspension_causa`, `salida_verificada`, `evidencia_ref` | toda automatizacion externa depende de gate |

## 5. Reglas canonicas clasificadas

### 5.1 Invariantes

- [Invariante] La suma de participaciones de una empresa o comunidad propietaria debe ser exactamente `100%`.
- [Invariante] Una propiedad no puede pertenecer simultaneamente a empresa y comunidad.
- [Invariante] Un contrato mantiene identidad durante toda su vida y se extiende mediante `PeriodoContractual`.
- [Invariante] Un cambio de arrendatario siempre genera termino del contrato anterior y nacimiento de un contrato nuevo.
- [Invariante] Una propiedad solo puede tener `1` contrato vigente y `1` contrato futuro.
- [Invariante] Una propiedad vinculada no puede tener contrato activo independiente.
- [Invariante] Un contrato solo puede cubrir `1` propiedad o `1` pareja `principal + vinculada`.
- [Invariante] La garantia pertenece al contrato, no a la propiedad individual.
- [Invariante] Un `PagoMensual` pertenece al contrato y no se duplica por propiedad vinculada.
- [Invariante] Todo `AsientoContable` debe cuadrar `debe = haber`.
- [Invariante] Un mismo hecho economico no puede generar doble contabilizacion efectiva para la misma empresa y periodo.
- [Invariante] Un periodo contable aprobado no admite edicion destructiva de asientos.
- [Invariante] La automatizacion contable-tributaria oficial del v1 solo opera para `Empresa` con `ConfiguracionFiscalEmpresa` activa bajo `RegimenTributarioEmpresa = EmpresaContabilidadCompletaV1`.
- [Invariante] La IA no decide por si sola la asignacion de pagos ambiguos ni la ejecucion de acciones juridicas o tributarias criticas.
- [Invariante] Ninguna credencial de canal o integracion pertenece a una cuenta bancaria por defecto; pertenece a una identidad o owner autorizado.

### 5.2 Policies v1

- [Policy v1] Los contratos activos del producto se modelan como mensuales: inicio dia `1`, termino ultimo dia y `dia_pago_mensual` entre `1` y `5`.
- [Policy v1] El monto minimo absoluto operativo es `CLP 1.000`.
- [Policy v1] Email es el canal base recomendado; WhatsApp es complementario y gated.
- [Policy v1] Las notificaciones tienen base sugerida `1/3/5/10/15/20/25`, pero se configuran por contrato.
- [Policy v1] Debe existir al menos un canal operativo por contrato.
- [Policy v1] WhatsApp opera solo dentro de ventana `08:00-21:00`.
- [Policy v1] El cierre de mes es automatico; la reapertura es excepcional y auditada.
- [Policy v1] LeaseManager lleva contabilidad nativa basada en ledger y asientos balanceados.
- [Policy v1] Todo mes operativo debe cerrar tambien como periodo contable antes de habilitar presentacion tributaria mensual.
- [Policy v1] El regimen tributario automatizable del set activo es unicamente `EmpresaContabilidadCompletaV1`.
- [Policy v1] La retencion minima de libros contables, DTE, F29, F22, DDJJ y soportes tributarios es de `6` anos calendario completos, ampliable mientras los antecedentes sirvan para periodos no prescritos, remanentes, amortizaciones, fiscalizaciones o litigios.
- [Policy v1] La retencion minima del expediente contractual, eventos auditables y respaldos operativos es de `6` anos desde termino de contrato o ultimo evento relevante, con `legal hold` cuando exista disputa o fiscalizacion.
- [Policy v1] Los exports sensibles generados por el sistema expiran en un maximo de `30` dias salvo hold legal o tributario.
- [Policy v1] La pareja `principal + vinculada` comparte cobro, garantia, aviso de termino y calendario.
- [Policy v1] El score de pago se expresa como `X% (Y de Z meses)` y excluye meses sin registro operativo.
- [Policy v1] El producto soporta `CLP` y `UF` como monedas operativas principales.
- [Policy v1] Si WhatsApp falla por bloqueo o error definitivo, el sistema registra el evento, marca el contacto, alerta al administrador y continua por email cuando exista.

### 5.3 Gates externos

- [Gate externo] La conciliacion bancaria automatica depende de un `ProviderBancario` activo y saludable.
- [Gate externo] La emision y presentacion tributaria dependen de la `CapacidadTributariaSII` aplicable, no de un bloque generico llamado "API SII".
- [Gate externo] WhatsApp depende de templates aprobados, numero habilitado, opt-in operativo y cumplimiento de ventanas y politicas del canal.
- [Gate externo] Email depende de `IdentidadDeEnvio` activa con OAuth o mecanismo autorizado por el ADR del canal.
- [Gate externo] La continuidad productiva posterior al `01/12/2026` depende del gate `Compliance.DatosPersonalesChile2026`.

### 5.4 Fallbacks permitidos y prohibidos

Fallbacks permitidos:

- `UF`: `BancoCentral -> CMF -> MiIndicador -> carga manual auditada`
- `Conciliacion bancaria`: match exacto -> asistido -> manual auditado
- `Motor contable`: contabilizacion automatica -> cola de revision -> resolucion manual auditada
- `Mensajeria`: WhatsApp disponible -> email -> alerta critica
- `SII`: capacidad abierta -> borrador y revision humana -> operacion manual controlada
- `Documentos`: flujo PDF canonico -> carga externa controlada con evidencia

Fallbacks prohibidos:

- `Provider bancario -> scraping`
- `Evento contable fallido -> desaparicion silenciosa`
- `Gate cerrado -> automatizacion silenciosa`
- `Pago ambiguo -> asignacion exacta por conveniencia`
- `Documento incompleto -> corregir despues sin evidencia`

### 5.5 Controles anti-inconsistencia y transiciones minimas

El sistema debe impedir o bloquear explicitamente:

- creacion de contrato futuro sin `AvisoTermino` o terminacion anticipada valida;
- cancelacion de `AvisoTermino` si existe contrato futuro no revertido;
- eliminacion de socio con participaciones activas;
- eliminacion de empresa con contratos, activos o mandatos operativos activos;
- aprobacion de cierre mensual con eventos contables pendientes o asientos descuadrados;
- cambios estructurales en propiedades vinculadas sin proceso explicito de division contractual;
- generacion de montos por debajo del minimo operativo;
- acceso de roles no autorizados a secretos, eventos sensibles o decisiones de cierre.

Transiciones minimas:

- `Contrato`: `PendienteActivacion -> Vigente`, `Vigente -> TerminadoAnticipadamente`, `Vigente -> Finalizado`, `Vigente -> Cancelado` solo si no produjo efectos irreversibles.
- `PagoMensual`: `Pendiente -> Pagado`, `Pendiente -> Atrasado`, `Atrasado -> EnRepactacion`, `EnRepactacion -> PagadoViaRepactacion`, `Pendiente/Atrasado -> PagadoPorAcuerdoDeTermino`.
- `AvisoTermino`: `Borrador -> Registrado`, `Registrado -> Cancelado` solo si no existe contrato futuro activo sin revertir.
- `EventoContable`: `PendienteContabilizacion -> Contabilizado`, `PendienteContabilizacion -> PendienteRevisionContable`, `PendienteRevisionContable -> Contabilizado`.
- `CierreMensualContable`: `Borrador -> Preparado`, `Preparado -> Aprobado`, `Aprobado -> Reabierto` solo por `AdministradorGlobal`.
- `ConexionBancaria`: `Verificando -> Activa`, `Verificando -> Pausada`, `Activa -> Pausada`, `Pausada -> Activa`, `Pausada/Activa -> Inactiva`.

Toda transicion critica debe generar `EventoAuditable`.

### 5.6 Reglas delegadas a ADR

- [ADR dependiente] framework de API y patrones de exposicion;
- [ADR dependiente] motor de colas y estrategia async;
- [ADR dependiente] motor documental y forma canonica de generacion;
- [ADR dependiente] gestion de secretos, certificados y tokens;
- [ADR dependiente] plan de cuentas base, journal ledger y motor contable nativo.

## 6. Formulas y reglas de calculo

### 6.1 Renta mensual activa

Secuencia canonica:

1. Obtener `monto_base` vigente desde `PeriodoContractual`.
2. Convertir a CLP si corresponde usando UF del dia `1` del mes operativo.
3. Aplicar `AjusteContrato` vigente.
4. Truncar decimales.
5. Validar minimo absoluto `CLP 1.000`.
6. Reemplazar los ultimos tres digitos por el `codigo_conciliacion_efectivo`.
7. Persistir el resultado como `monto_calculado_clp`.

Ejemplo conceptual:

```text
monto_truncado = 523456
codigo_conciliacion_efectivo = 042
resultado = 523042
```

Reglas:

- el codigo efectivo de una pareja vinculada es siempre el de la propiedad principal;
- el sistema no redondea;
- la insercion de codigo se usa solo para cobros de contratos activos.

### 6.2 Cobranza residual post-contrato

Secuencia canonica:

1. Consolidar saldo residual desde deuda historica, retenciones y acuerdos de termino.
2. Crear caso de cobranza con `CodigoCobroResidual`.
3. Emitir instruccion de pago con `referencia_visible` y monto exigible.
4. Intentar match exacto solo si el provider entrega referencia confiable.
5. Si no hay referencia confiable, operar en modo asistido o manual con trazabilidad completa.

Reglas:

- `CodigoCobroResidual` no reemplaza codigo de propiedad;
- el cobro residual no usa el namespace `001-999`;
- el arrendatario puede tener contratos nuevos y mantener casos de cobranza residual abiertos sin colision operacional.

## 7. Flujos criticos

### 7.1 Alta de arrendatario

1. El operador registra email inicial.
2. El sistema envia formulario externo con expiracion.
3. El prospecto completa datos.
4. El operador revisa y aprueba o rechaza.
5. Si se aprueba, nace el `Arrendatario` con trazabilidad del origen.

### 7.2 Activacion operativa de una propiedad

1. Registrar o validar `Propiedad`, `Propietario` y participaciones.
2. Configurar `CuentaRecaudadora`.
3. Registrar `MandatoOperacion`.
4. Asignar `IdentidadDeEnvio` por canal.
5. Validar gates de integraciones aplicables.
6. Dejar la propiedad elegible para contratar.

### 7.3 Creacion de contrato

1. Seleccionar propiedad unica o pareja `principal + vinculada`.
2. Validar `MandatoOperacion`, elegibilidad patrimonial y ausencia de conflictos con contratos activos o futuros.
3. Seleccionar `Arrendatario` y eventuales `CodeudoresSolidarios`.
4. Definir periodos, monto, moneda, garantia, notificaciones y overrides de canal si corresponden.
5. Generar vista previa de periodos, cobros y documentos.
6. Confirmar contrato y crear expediente documental.

### 7.4 Ciclo mensual

1. Obtener UF desde la cadena activa.
2. Generar `PagoMensual`.
3. Emitir documento tributario solo si la capacidad SII aplicable tiene gate abierto.
4. Enviar comunicaciones por identidades activas.
5. Conciliar movimientos bancarios.
6. Generar `EventoContable` para hechos economicos confirmados.
7. Actualizar estado de cuenta, score y dashboard.
8. Cerrar mes al final del periodo; reabrir solo bajo excepcion auditada.

### 7.5 Cierre mensual contable y tributario

1. Consolidar `EventoContable` y verificar que no existan pendientes sin resolver.
2. Generar `AsientoContable`, `LibroDiario`, `LibroMayor` y `BalanceComprobacion` del periodo.
3. Calcular `ObligacionTributariaMensual`.
4. Preparar borrador de `F29` si la capacidad correspondiente tiene gate abierto.
5. Presentar al `AdministradorGlobal` el resumen de cierre mensual.
6. Aprobar `CierreMensualContable` o devolverlo a revision.
7. Si aparece un hecho economico posterior al cierre, aplicar `PoliticaReversoContable` mediante reverso, asiento complementario o reapertura controlada.

### 7.6 Degradacion bancaria

1. El provider bancario entra en suspension.
2. La `CuentaRecaudadora` pasa a modo degradado.
3. Se alerta al administrador.
4. Se habilita carga y asignacion manual de movimientos.
5. Toda asignacion manual genera `ResolucionManual` y `EventoAuditable`.

### 7.7 Terminacion y cobranza residual

1. Registrar causal y fecha efectiva.
2. Consolidar ultimo mes, deuda y tratamiento de garantia.
3. Cerrar o regularizar garantia contractual.
4. Si queda saldo, crear `CodigoCobroResidual`.
5. Emitir documentos de termino y plan de cobro residual.
6. Mantener trazabilidad del contrato origen sin reciclar su identidad.

### 7.8 Ciclo documental

1. Generar borrador documental desde plantilla versionada.
2. Revisar por operador y contraparte segun `PoliticaFirmaYNotaria`.
3. Emitir PDF canonico.
4. Registrar firma, aprobacion o recepcion notarial cuando corresponda.
5. Archivar en `ExpedienteDocumental` con checksum y version.

### 7.9 Proceso anual de renta

1. Consolidar doce `CierreMensualContable` aprobados y su ledger anual.
2. Generar `ProcesoRentaAnual` con resumen de resultados, bases y observaciones.
3. Preparar paquetes de `DDJJ` y borrador `F22` si los gates correspondientes estan abiertos.
4. Presentar al `AdministradorGlobal` el resumen anual y los riesgos detectados.
5. Aprobar o rechazar la salida anual final; si se aprueba, ejecutar solo las capacidades abiertas para presentacion.
6. Si el regimen tributario de la empresa no es `EmpresaContabilidadCompletaV1`, el sistema bloquea la preparacion anual oficial y solo permite reporting.

## 8. Capacidades externas y relacion con gates

| Capacidad | Descripcion canonica | Artefacto de control |
|---|---|---|
| `Banca.Movimientos` | ingesta de movimientos para conciliacion | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |
| `UF.Fuentes` | obtencion de valor UF y fallback auditado | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |
| `Email.Salida` | envio contractual y operacional por identidades activas | [ADR_ARQUITECTURA_002_IDENTIDAD_ENVIO.md](./ADR_ARQUITECTURA_002_IDENTIDAD_ENVIO.md) |
| `WhatsApp.Salida` | recordatorios y avisos por canal habilitado | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |
| `SII.DTE*` | emision y consulta tributaria documental | [ADR_ARQUITECTURA_003_CAPACIDADES_SII.md](./ADR_ARQUITECTURA_003_CAPACIDADES_SII.md) |
| `SII.F29*` | preparacion y eventual presentacion mensual | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |
| `SII.DDJJ*` | preparacion anual de declaraciones juradas | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |
| `SII.F22*` | preparacion anual de renta | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |
| `Compliance.DatosPersonalesChile2026` | readiness regulatorio para operar despues del `01/12/2026` | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) |

## 9. Seguridad, resiliencia, observabilidad y data protection

### 9.1 Seguridad minima obligatoria

- todo acceso de usuario opera por HTTPS y sesiones seguras;
- todo secreto y certificado se gestiona segun el ADR de secretos;
- `Socio` y `RevisorFiscalExterno`, cuando se configure, no acceden a secretos de integracion;
- toda lectura, exportacion y dashboard debe respetar el scope operativo del rol, empresa, socio o mandato correspondiente;
- toda accion sensible registra actor, timestamp, entidad afectada y motivo;
- no existe cambio retroactivo silencioso en meses cerrados;
- no existe asignacion automatica de pagos ambiguos.

### 9.2 Data protection

- el producto debe separar datos operativos, documentos y secretos;
- el producto debe segregar correctamente informacion entre carteras, empresas y socios segun su ambito autorizado;
- los datos sensibles deben clasificarse al menos como `operativo`, `financiero`, `tributario`, `documental sensible` y `secreto`;
- toda resolucion manual debe dejar evidencia recuperable;
- si la plataforma entra o sigue en produccion despues del `1 de diciembre de 2026`, el gate `Compliance.DatosPersonalesChile2026` debe estar abierto;
- `PoliticaRetencionDatos` se define como entidad canonica activa y no depende de backlog para operar el v1.
- libros contables, DTE, F29, F22, DDJJ y soportes tributarios se conservan por minimo `6` anos calendario completos, ampliables por remanentes, amortizaciones, fiscalizacion o litigio;
- expediente contractual, documentos notariales y eventos auditables se conservan por minimo `6` anos desde termino del contrato o ultimo evento relevante;
- un export sensible generado por la plataforma debe quedar cifrado, con motivo, scope y expiracion maxima de `30` dias salvo hold legal o tributario.

### 9.3 Resiliencia y continuidad

- si falla cache o cola, el sistema debe continuar en modo degradado controlado;
- un error de una propiedad o contrato no debe bloquear el procesamiento masivo completo;
- objetivo operacional inicial: `RPO 24h` y `RTO 4h`;
- backups incrementales diarios y completos semanales.

### 9.4 Observabilidad

Minimos obligatorios:

- salud de integraciones y gates;
- latencia de calculo mensual;
- fallos documentales;
- colas y tareas;
- movimientos sin match;
- bloqueos o errores definitivos de WhatsApp;
- reaperturas de mes y otras excepciones criticas.

## 10. Roadmap de activacion

El roadmap ya no congela features por herencia historica; activa capacidades solo cuando dominio, gates y ADR lo permiten.

### Fase 1. Nucleo operacional

- patrimonio, mandato operacional y contratos;
- calculo mensual con `codigo_conciliacion_efectivo`;
- conciliacion bancaria exacta o manual;
- `EventoContable`, `AsientoContable` y ledger nativo;
- expediente documental;
- notificaciones por email;
- garantias y deuda base;
- acceptance transaccional y de permisos.

### Fase 2. Operacion asistida

- conciliacion asistida;
- cierre mensual contable y tributario;
- `F29Preparacion` con borrador aprobable por `AdministradorGlobal`;
- WhatsApp gated;
- firma y formalizacion documental;
- score de pago y reporting operativo;
- primeros flujos SII documentales con gate abierto.

### Fase 3. Cobranza avanzada y reporting financiero

- `CodigoCobroResidual`;
- repactaciones completas;
- libros y reportes contables nativos;
- reporting filtrado para socios;
- mejoras de productividad operacional.

### Fase 4. Preparacion anual y cierre regulatorio

- `DDJJPreparacion` y `F22Preparacion`;
- consolidacion anual de `ProcesoRentaAnual`;
- endurecimiento de retencion, exportacion y compliance regulatorio;
- reporting financiero y anual consolidado.

### Fase 5. Escalamiento operativo del core

- `F29Presentacion` solo si su gate especifico esta abierto;
- presentaciones anuales finales solo si su gate especifico esta abierto;
- nunca auto-presentacion critica sin gate y politica de aprobacion expresa.

## 11. Acceptance ejecutable

### 11.1 Criterios globales

Toda capacidad aceptada debe:

- ser coherente con el dominio y con su clasificacion (`Invariante`, `Policy v1`, `Gate externo` o `ADR dependiente`);
- funcionar en caso normal, degradado y manual cuando aplique;
- registrar trazabilidad suficiente;
- respetar permisos y boundaries;
- estar cubierta por criterios de aceptacion verificables.

### 11.2 Matriz minima por subsistema

| Subsistema | Debe probarse al menos con | Resultado esperado |
|---|---|---|
| Patrimonio | propiedad de empresa y propiedad en comunidad | validaciones `100%` y representacion correcta |
| Operacion | mandato operativo con recaudador, facturador e identidad de envio distintos | el sistema resuelve sin confundir ownership |
| Contratos | contrato estandar, renovacion, aviso de termino, contrato futuro | no se duplica identidad y se respetan policies v1 |
| Propiedades vinculadas | pareja `principal + vinculada` | un cobro unico, un codigo efectivo, trazabilidad por propiedad |
| Cobranza activa | generacion de `PagoMensual` con UF, ajuste y truncado | formula canonica correcta |
| Cobranza residual | termino con deuda residual y `CodigoCobroResidual` | no hay colision con codigos de propiedad |
| Conciliacion | match exacto, asistido y manual | ningun pago ambiguo se autoasigna |
| Contabilidad | `EventoContable`, `AsientoContable`, cierre mensual y ledger | todo asiento cuadra y el periodo cierra sin pendientes |
| Fiscalidad de empresa | `ConfiguracionFiscalEmpresa`, regimen soportado y cierre tributario | solo empresas dentro del regimen soportado pasan a preparacion oficial |
| Garantias | recepcion, devolucion parcial, retencion parcial y cierre | historial completo y coherente |
| Documentos | politica de firma y notaria por tipo documental | el documento no se formaliza sin los requisitos configurados |
| Canales | email activo y WhatsApp suspendido | el sistema usa solo canales permitidos y alerta correctamente |
| SII | gate cerrado y gate abierto por capacidad | solo la capacidad abierta opera y las presentaciones finales requieren `AdministradorGlobal` |
| Boundary activo | regimen soportado y capacidades no podadas | el sistema bloquea automatizaciones fuera del boundary activo |
| Seguridad y auditoria | reapertura de mes, resolucion manual, acceso restringido, exportacion sensible | evidencia completa y permisos correctos |

### 11.3 Escenarios transversales obligatorios

1. Contrato estandar de una propiedad.
2. Contrato con `principal + vinculada`.
3. Renovacion por `PeriodoContractual`.
4. Cambio de arrendatario mediante termino y contrato nuevo.
5. Contrato retroactivo dentro de policies v1.
6. Falla del provider bancario con resolucion manual.
7. Garantia completa, parcial, devolucion y retencion.
8. Aviso de termino con contrato futuro.
9. Deuda residual con `CodigoCobroResidual`.
10. Email operativo con WhatsApp suspendido.
11. Cierre mensual contable aprobado con `F29Preparacion` generada.
12. `DDJJPreparacion` y `F22Preparacion` generadas desde doce cierres aprobados.
13. SII con `DTEEmision` abierta y `F29Presentacion` cerrada.
14. Reverso o asiento complementario posterior a cierre aplicado segun politica canonica.
15. Exportacion sensible fuera de scope rechazada por permisos.
16. Empresa fuera de `EmpresaContabilidadCompletaV1` bloqueada para automatizacion tributaria oficial.
17. Capacidad podada no reaparece como activa en roadmap, gates ni acceptance.

## 12. Glosario minimo

| Termino | Definicion canonica |
|---|---|
| `MandatoOperacion` | relacion operativa vigente que une activo, operador, recaudacion, facturacion y canales |
| `CuentaRecaudadora` | cuenta o instrumento sobre el que se esperan los cobros |
| `IdentidadDeEnvio` | identidad autenticada usada para un canal de salida |
| `ProviderBancario` | adapter conceptual que expone movimientos, saldos y conectividad |
| `CodigoConciliacionEfectivo` | codigo de tres digitos embebido en el cobro mensual activo |
| `CodigoCobroResidual` | referencia visible de cobranza post-contrato sin colision con el namespace de propiedad |
| `RegimenTributarioEmpresa` | regimen fiscal soportado por la automatizacion oficial del v1 |
| `ConfiguracionFiscalEmpresa` | configuracion fiscal necesaria para cierres y preparacion tributaria |
| `EventoContable` | hecho economico canonico listo para contabilizar |
| `AsientoContable` | journal entry balanceado generado por el motor contable |
| `CierreMensualContable` | cierre auditable del periodo mensual contable y tributario |
| `ProcesoRentaAnual` | consolidacion anual para DDJJ y F22 |
| `PoliticaRetencionDatos` | politica canonica de conservacion, exportacion y hold de datos sensibles |
| `PoliticaFirmaYNotaria` | politica documental que define firmas y notaria exigidas |
| `PoliticaReversoContable` | politica que define reversos, ajustes y reaperturas despues del cierre |
| `Policy v1` | decision de producto vigente solo para esta version del boundary |
| `Gate externo` | condicion formal que habilita, suspende o reabre una capacidad dependiente de terceros |
| `ResolucionManual` | decision humana auditable aplicada cuando el flujo automatico no es seguro |

## 13. Mapeo desde el PRD maestro previo

| Seccion previa | Destino en el nuevo set | Disposicion |
|---|---|---|
| `1. Estatus del documento` | este PRD `1` | reescrita |
| `2. Metodologia de consolidacion` | historico + auditoria maxima | movida a historico |
| `3. Vision del producto` | este PRD `2` | reescrita |
| `4. Principios rectores` | este PRD `1`, `5`, `9` | dividida |
| `5. Localizacion, usuarios y KPIs` | este PRD `2`, `3`, `11` | reescrita |
| `6. Alcance funcional` | este PRD `2`, `10` | reescrita |
| `7. Modelo de dominio y definiciones canonicas` | este PRD `4` | reescrita profundamente |
| `8. Reglas de negocio definitivas` | este PRD `5` y `6` | reescrita y reclasificada |
| `9. Flujos operacionales criticos` | este PRD `7` | mantenida y ampliada |
| `10. Integraciones externas y condiciones de activacion` | [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md) + este PRD `8` + ADR-001/002/003/008 | dividida |
| `11. Requisitos de seguridad, resiliencia y auditoria` | este PRD `9` + ADR-006/008 | dividida |
| `12. Requisitos tecnicos y de UX` | ADR-004/005/006/008 | movida a ADR |
| `13. Roadmap maestro` | este PRD `10` | reescrita |
| `14. Fuera de alcance` | este PRD `2.2` | integrada |
| `15. Criterios de aceptacion y validacion` | este PRD `11` | reescrita |
| `16. Formulas y limites` | este PRD `6` | mantenida y corregida |
| `17. Configuracion externa requerida` | ADR + matriz de gates | movida |
| `18. Trazabilidad por version` | historico auditado | movida a historico |
| `19. Documentos de apoyo considerados` | historico auditado | movida a historico |
| `20. Matriz resumida de decisiones canonicas` | este PRD + ADR + gates | reemitida por separacion |
| `21. Glosario minimo` | este PRD `12` | ampliada |

