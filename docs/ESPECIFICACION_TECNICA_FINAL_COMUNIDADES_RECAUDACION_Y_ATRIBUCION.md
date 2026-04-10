# Especificacion Tecnica Final - Comunidades, Recaudacion y Atribucion Economica

Fecha: 2026-04-05
Estado: base tecnica definitiva para implementacion
Scope: `Patrimonio`, `Operacion`, `Cobranza`, `Conciliacion`, `Contabilidad`, `SII`, `Reporting`, `migration`

## 1. Objetivo

Fijar el diseno tecnico definitivo para resolver de forma integra y estable:

- comunidades patrimoniales reales;
- separacion entre administracion operativa y recaudacion bancaria;
- comunidades mixtas con participantes `Socio` o `Empresa`;
- recaudacion del 100% del contrato sin confundirla con la fraccion economicamente atribuible o facturable;
- casos reales como comunidades estandar, `Santa Maria II`, `Edificio Q`, propiedades personales y empresas normales.

Esta especificacion reemplaza cualquier solucion parcial o transitoria para este problema.

## 2. Problema que debe quedar resuelto

El sistema actual mezcla tres planos que no siempre coinciden:

1. quien es dueno economico del activo;
2. quien administra operativamente el arriendo;
3. quien recibe bancariamente el dinero;
4. quien puede facturar una fraccion del flujo;
5. a quien se le atribuye economicamente el cobro.

Mientras esos planos sigan mezclados:

- una empresa puede aparecer como administradora solo por ser titular de la cuenta;
- un pago comunitario puede terminar tratado como ingreso de empresa por fallback tecnico;
- `Edificio Q` queda forzado a una excepcion;
- el backend sigue representando mal la realidad operativa.

## 3. Decisiones de dominio definitivas

### 3.1 Roles operativos definitivos

`MandatoOperacion` debe declarar siempre cuatro roles distintos:

- `Propietario`
- `AdministradorOperativo`
- `Recaudador`
- `EntidadFacturadora`

La separacion no es opcional.

### 3.2 Regla definitiva de recaudacion

`CuentaRecaudadora` sigue siendo la fuente de verdad bancaria.

Regla definitiva:

- la `CuentaRecaudadora` debe pertenecer exactamente al `Recaudador`;
- el `Recaudador` debe declararse explicitamente en `MandatoOperacion`;
- el owner de la cuenta y el `Recaudador` no pueden divergir.

Esto evita duplicacion semantica y evita que el rol de recaudacion quede como un campo libre capaz de contradecir la cuenta real.

### 3.3 Regla definitiva de comunidades

`ComunidadPatrimonial` debe soportar participantes activos de dos tipos:

- `Socio`
- `Empresa`

La suma activa sigue siendo exactamente `100.00`.

### 3.4 Regla definitiva de representante

`Representante` de comunidad no se mezcla con `AdministradorOperativo`.

Diseno definitivo:

- el representante vive en `Patrimonio`;
- el administrador vive en `MandatoOperacion`;
- el representante puede ser:
  - `participante_patrimonial`
  - `designado`
- en ambos casos, dentro del boundary actual, el representante es un `Socio`.

Esto cubre los dos caminos reales ya detectados:

- comunidad representada por un copropietario;
- comunidad administrada por Joaquin aunque no tenga participacion patrimonial en esa comunidad.

Regla cerrada para el backlog/migracion actual:

- las comunidades actualmente en construccion dentro de esta base deben usar a `Joaquin Puig Vittini` como `representante_designado`, salvo evidencia primaria futura en contrario.

Regla cerrada para participaciones legacy sin `vigente_desde`:

- debe usarse `2017-03-16` como `vigente_desde` canonico por defecto;
- esta fecha corresponde al hito simbolico de herencia y administracion actual confirmado por el usuario;
- no debe abrirse `ManualResolution` por `missing_vigencia` cuando el unico faltante sea esa fecha.

Regla cerrada para region legacy faltante en este backlog:

- cuando la propiedad legacy tenga `comuna` o `ciudad = Temuco` y la `region` venga vacia, debe completarse como `La Araucania`;
- no debe bloquearse la resolucion manual de comunidades de Temuco por ausencia de region en el extracto.

### 3.5 Regla definitiva de atribucion economica

`PagoMensual` sigue representando el cobro total del contrato.

Pero:

- `PagoMensual` no es la fuente directa de verdad para facturacion, contabilidad ni reporting economico;
- debe existir una capa derivada explicita que represente como ese cobro se atribuye economicamente.

Sin esa capa, el caso `Edificio Q` no queda correctamente resuelto.

## 4. Modelo final por bounded context

### 4.1 Patrimonio

#### 4.1.1 `ParticipacionPatrimonial`

El modelo deja de usar una sola FK `socio`.

Diseno final:

- `participante_socio` nullable
- `participante_empresa` nullable
- `empresa_owner` nullable
- `comunidad_owner` nullable
- `porcentaje`
- `vigente_desde`
- `vigente_hasta`
- `activo`

Invariantes:

- cada participacion pertenece exactamente a un owner: `Empresa` o `ComunidadPatrimonial`;
- cada participacion apunta exactamente a un participante: `Socio` o `Empresa`;
- si `owner = Empresa`, el participante permitido dentro del boundary actual es solo `Socio`;
- si `owner = ComunidadPatrimonial`, el participante permitido es `Socio` o `Empresa`;
- la suma activa por owner debe ser exactamente `100.00`.

Campos derivados recomendados:

- `participante_tipo`
- `participante_id`

#### 4.1.2 `RepresentacionComunidad`

El campo actual `representante_socio` en `ComunidadPatrimonial` debe reemplazarse por una entidad explicita y versionable.

Diseno final:

- `comunidad`
- `modo_representacion`:
  - `participante_patrimonial`
  - `designado`
- `socio_representante`
- `vigente_desde`
- `vigente_hasta`
- `activo`
- `observaciones`

Invariantes:

- una comunidad activa debe tener exactamente una representacion activa vigente;
- si `modo_representacion = participante_patrimonial`, el `socio_representante` debe existir en las participaciones activas `participante_socio` de esa comunidad;
- si `modo_representacion = designado`, el `socio_representante` solo debe ser un `Socio` activo;
- `RepresentacionComunidad` y `AdministradorOperativo` pueden coincidir, pero no dependen entre si.

Motivo:

- permite resolver hoy el dilema semantico del representante sin volver a tocar schema despues;
- agrega historia y evita esconder cambios de representacion dentro del mismo row de comunidad.

### 4.2 Operacion

#### 4.2.1 `CuentaRecaudadora`

Se mantiene como hoy en su ownership simple:

- `empresa_owner` o `socio_owner`

No se agrega `comunidad_owner`.

Razon:

- las comunidades reales usan cuentas de empresa o socio;
- no hay evidencia de cuentas bancarias propias de la comunidad como entidad operativa distinta.

#### 4.2.2 `MandatoOperacion`

Diseno final:

- `propietario_empresa_owner` / `propietario_comunidad_owner` / `propietario_socio_owner`
- `administrador_empresa_owner` / `administrador_socio_owner`
- `recaudador_empresa_owner` / `recaudador_socio_owner`
- `entidad_facturadora`
- `cuenta_recaudadora`
- `tipo_relacion_operativa`
- `autoriza_recaudacion`
- `autoriza_facturacion`
- `autoriza_comunicacion`
- `vigencia_desde`
- `vigencia_hasta`
- `estado`

Invariantes:

- exactamente un `Propietario`;
- exactamente un `AdministradorOperativo`;
- exactamente un `Recaudador`;
- `EntidadFacturadora` es opcional, pero si existe debe ser `Empresa`;
- la `CuentaRecaudadora` debe pertenecer exactamente al `Recaudador`;
- `autoriza_recaudacion = true` si `Recaudador != Propietario`;
- `autoriza_comunicacion = true` si `AdministradorOperativo != Propietario`;
- `autoriza_facturacion = true` si `EntidadFacturadora` existe y `EntidadFacturadora != Propietario`.

Reglas especiales para propietarios comunidad:

- si la comunidad no tiene participantes `Empresa` activos, `EntidadFacturadora` debe ser `null`;
- si la comunidad tiene exactamente un participante `Empresa` activo y el flujo requiere facturacion, `EntidadFacturadora` debe coincidir con ese participante;
- si la comunidad tiene mas de un participante `Empresa` activo, el ownership patrimonial puede existir, pero la automatizacion tributaria de ese contrato queda fuera del boundary actual y el mandato no puede activarse con `EntidadFacturadora` automatica.

Razon:

- el PRD activo modela `EntidadFacturadora` singular;
- no hay evidencia suficiente para abrir hoy multiples facturadoras automaticas por un mismo mandato.

### 4.3 Canales

Sin cambio de concepto.

`IdentidadDeEnvio` sigue perteneciendo solo a:

- `AdministradorOperativo`
- `EntidadFacturadora`

Nunca:

- `CuentaRecaudadora`
- `Recaudador` por el solo hecho de recaudar

Invariantes:

- las credenciales de canal no se atan a cuentas bancarias;
- la identidad activa de un mandato debe pertenecer al administrador o a la facturadora.

### 4.4 Cobranza

#### 4.4.1 `PagoMensual`

Se mantiene como cobro total del contrato:

- un row por contrato/mes;
- `monto_facturable_clp` total teorico pre-codigo;
- `monto_calculado_clp` total cobrable con codigo;
- `monto_pagado_clp` total efectivamente conciliado;
- `codigo_conciliacion_efectivo` del contrato.

No se fragmenta `PagoMensual`.

Razon:

- la conciliacion bancaria del sistema esta pensada sobre un cobro unico por contrato.

#### 4.4.2 Nueva entidad: `DistribucionCobroMensual`

Debe introducirse una entidad nueva, derivada de `PagoMensual`.

Diseno final:

- `pago_mensual`
- `beneficiario_socio_owner` nullable
- `beneficiario_empresa_owner` nullable
- `porcentaje_snapshot`
- `monto_devengado_clp`
- `monto_conciliado_clp`
- `monto_facturable_clp`
- `requiere_dte`
- `origen_atribucion`
- `created_at`
- `updated_at`

Invariantes:

- cada linea pertenece exactamente a un beneficiario: `Socio` o `Empresa`;
- por `PagoMensual`, la suma de `monto_devengado_clp` debe ser exactamente igual a `pago_mensual.monto_facturable_clp`;
- por `PagoMensual` pagado, la suma de `monto_conciliado_clp` debe ser exactamente igual a `pago_mensual.monto_pagado_clp`;
- una linea con `requiere_dte = true` debe tener beneficiario `Empresa`;
- una linea con `requiere_dte = true` debe coincidir con `MandatoOperacion.entidad_facturadora`.

Generacion:

- si `Propietario = Empresa`: una linea 100% a la empresa;
- si `Propietario = Socio`: una linea 100% al socio;
- si `Propietario = Comunidad`: una linea por cada participacion activa snapshot de esa comunidad al momento de generar el pago.

Observacion:

- esta entidad es la capa estable que separa `recaudacion del 100%` de `beneficio economico / facturacion`.

### 4.5 Conciliacion

La conciliacion sigue matcheando por `CuentaRecaudadora` y `PagoMensual`.

Cambio final:

- una vez conciliado el pago, debe poblar o confirmar `monto_conciliado_clp` en `DistribucionCobroMensual`;
- no debe resolver empresa por owner de cuenta;
- la recaudacion bancaria queda separada de la atribucion economica.

### 4.6 SII

`DTEEmitido` ya no debe depender solo de `PagoMensual`.

Diseno final:

- `DTEEmitido` mantiene referencia a `contrato` y `pago_mensual`;
- agrega referencia obligatoria a `distribucion_cobro_mensual`;
- `monto_neto_clp` del DTE sale desde la linea facturable, no desde el pago total;
- `empresa` del DTE debe coincidir con el beneficiario empresa de esa linea.

Invariantes:

- un DTE no puede emitirse desde una distribucion no facturable;
- una distribucion facturable no puede pertenecer a un socio;
- la empresa del DTE debe ser la empresa beneficiaria/facturadora de la distribucion.

### 4.7 Contabilidad

La contabilidad automatica empresarial deja de resolver una sola empresa por pago.

Diseno final:

- un pago conciliado puede generar cero, una o varias lineas de distribucion;
- `Contabilidad` solo genera `EventoContable` automatico para lineas cuyo beneficiario sea `Empresa`;
- las lineas de `Socio` no entran al ledger empresarial;
- los flujos de comunidad sin empresa beneficiaria no deben caer por fallback a la empresa dueña de la cuenta.

Consecuencia:

- `resolve_empresa_for_payment` debe desaparecer como regla central;
- debe reemplazarse por generacion desde `DistribucionCobroMensual`.

### 4.8 Reporting

`Reporting` financiero por empresa debe agregarse desde:

- `DistribucionCobroMensual` para cobros atribuibles/facturables;
- `EventoContable` para lo efectivamente posteado en empresa.

Queda prohibido:

- contar un pago como ingreso de empresa solo porque entro por una cuenta de empresa.

## 5. Reglas operativas definitivas por tipo de caso

### 5.1 Empresa normal

- `Propietario = Empresa`
- `AdministradorOperativo = Empresa` o tercero autorizado
- `Recaudador = owner de la cuenta`
- `EntidadFacturadora = Empresa`
- `DistribucionCobroMensual`: una linea 100% a la empresa, facturable

### 5.2 Propiedad personal

- `Propietario = Socio`
- `AdministradorOperativo` segun operacion real
- `Recaudador = owner de la cuenta`
- `EntidadFacturadora = null`
- `DistribucionCobroMensual`: una linea 100% al socio, no facturable

### 5.3 Comunidad estandar

- `Propietario = ComunidadPatrimonial`
- participantes solo `Socio`
- `AdministradorOperativo = Joaquin`
- `Recaudador = Santa Maria Ltda`
- `CuentaRecaudadora = 8240452907`
- `EntidadFacturadora = null`
- `DistribucionCobroMensual`: una linea por socio, ninguna facturable

### 5.4 Comunidad mixta tipo `Edificio Q`

- `Propietario = ComunidadPatrimonial`
- participantes:
  - socios
  - `Inmobiliaria Puig SpA`
- `AdministradorOperativo` segun operacion real
- `Recaudador` segun owner real de la cuenta usada
- `EntidadFacturadora = Inmobiliaria Puig SpA`
- `PagoMensual`: 100% del arriendo
- `DistribucionCobroMensual`: una linea por participante
- solo la linea de `Inmobiliaria Puig SpA` es facturable

Resultado:

- se cobra el 100%;
- se factura solo la fraccion de la empresa;
- no se confunde recaudacion total con beneficio de empresa.

## 6. Decisiones tecnicas derivadas e invariantes globales

### 6.1 Invariantes globales

- una comunidad activa debe tener participaciones activas que sumen exactamente `100.00`;
- un mandato activo debe tener exactamente un `Recaudador`;
- la cuenta recaudadora de un mandato activo debe pertenecer al `Recaudador`;
- la identidad de envio de un mandato activo no depende del recaudador ni de la cuenta;
- `PagoMensual` representa el total del contrato;
- `DistribucionCobroMensual` representa la atribucion economica del cobro;
- `SII`, `Contabilidad` y `Reporting` deben apoyarse en `DistribucionCobroMensual`, no en el owner de la cuenta.

### 6.2 Regla definitiva sobre mejoras futuras

Esta especificacion ya deja resuelto:

- representante participante o designado;
- comunidad solo de socios o mixta;
- cuenta compartida de comunidades;
- empresa con fraccion facturable dentro de comunidad;
- separacion entre cobro total y atribucion economica.

Por lo tanto, la implementacion no debe introducir parches locales que contradigan estas piezas.

## 7. Impacto de implementacion por modulo

### 7.1 `backend/patrimonio`

- cambiar `ParticipacionPatrimonial` para soportar `participante_socio` o `participante_empresa`;
- introducir `RepresentacionComunidad`;
- actualizar serializers, views, admin y tests;
- actualizar validaciones de comunidad activa.

### 7.2 `backend/operacion`

- agregar `recaudador_empresa_owner` / `recaudador_socio_owner`;
- actualizar `clean()` de `MandatoOperacion`;
- actualizar serializer, vistas y tests;
- ajustar validacion de cuenta para que amarre con `Recaudador`.

### 7.3 `backend/cobranza`

- mantener `PagoMensual`;
- crear `DistribucionCobroMensual`;
- generar snapshot de distribucion al crear pago;
- adaptar tests de calculo y generacion.

### 7.4 `backend/conciliacion`

- al conciliar un pago, completar `monto_conciliado_clp` por distribucion;
- dejar de depender de fallback por cuenta para inferir empresa.

### 7.5 `backend/sii`

- agregar FK de `DTEEmitido` a `DistribucionCobroMensual`;
- generar borrador DTE desde la linea facturable;
- adaptar tests para comunidad mixta.

### 7.6 `backend/contabilidad`

- eliminar resolucion unica de empresa por pago;
- generar eventos por distribucion empresa;
- no postear eventos automaticos para lineas de socio.

### 7.7 `backend/reporting`

- reescribir agregaciones por empresa usando distribucion y/o eventos contables;
- mantener dashboards operativos basados en pago total donde corresponda;
- separar claramente `cobrado_total` de `atribuido_empresa_total`.

### 7.8 `migration`

- adaptar bundle para participantes empresa en comunidad;
- adaptar resolucion manual de owner comunitario;
- eliminar supuesto de `representante_socio` obligatorio dentro de las participaciones;
- permitir resolucion de comunidad con representacion designada.

## 8. Secuencia de implementacion obligatoria

1. `Patrimonio`
2. `Operacion`
3. `Cobranza`
4. `SII`
5. `Contabilidad`
6. `Reporting`
7. `migration`
8. rerun controlado de casos bloqueados

Razon:

- si se toca primero `Contabilidad` o `Reporting`, seguirian sin existir las nuevas fuentes de verdad;
- si se toca primero `migration`, se volveria a empujar backlog real sobre un modelo aun incompleto.

## 9. Criterios de aceptacion definitivos

Debe poder probarse al menos:

1. Comunidad estandar con representante participante.
2. Comunidad estandar con representante designado no participante.
3. Comunidad mixta con una empresa participante facturable.
4. Cuenta recaudadora de empresa distinta del administrador.
5. `PagoMensual` unico del 100% con `DistribucionCobroMensual` en varias lineas.
6. DTE generado solo por la fraccion empresa de una comunidad mixta.
7. Contabilidad empresarial creada solo para lineas empresa.
8. Reporting por empresa sin contaminarse por simple owner de cuenta.

## 10. Resultado esperado

Cuando esta especificacion este implementada:

- el sistema podra describir fielmente quien administra;
- podra describir fielmente quien recauda;
- podra describir fielmente quien factura;
- podra distinguir cobro total de atribucion economica;
- y dejara de necesitar excepciones ad hoc para comunidades y `Edificio Q`.
