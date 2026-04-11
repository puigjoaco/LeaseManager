# PRD Maestro Definitivo - LeaseManager

> Estado actual: documento historico auditado. La fuente vigente de producto es [PRD_CANONICO.md](./PRD_CANONICO.md). Las decisiones de implementacion delegadas viven en los `ADR_ARQUITECTURA_*` y la activacion real de integraciones externas vive en [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md).

## 1. Estatus del documento

Este documento es la referencia canónica de producto para **LeaseManager**, antes conocido como **Rent Control** y también referido en materiales históricos como **Lease Manager**. Consolida, corrige y supera el contenido de:

- [prd.txt](D:/Proyectos/PRDLeaseManager/prd.txt)
- [PRD_UNIFICADO.md](D:/Proyectos/PRDLeaseManager/PRD_UNIFICADO.md)
- [CLAUDE.md](D:/Proyectos/PRDLeaseManager/CLAUDE.md)
- Los 26 PRD crudos de [analizar](D:/Proyectos/PRDLeaseManager/analizar)

Desde este punto:

- Este archivo es la fuente oficial de verdad del producto.
- Los demás documentos quedan como material histórico y de trazabilidad.
- Cuando exista conflicto entre versiones previas y este documento, prevalece este documento.
- La auditoría detallada por versión vive separada en [AUDITORIA_PRDS_1_26.md](D:/Proyectos/PRDLeaseManager/AUDITORIA_PRDS_1_26.md).
- La consolidación transversal por tema vive separada en [MATRIZ_CONSOLIDACION_TEMATICA.md](D:/Proyectos/PRDLeaseManager/MATRIZ_CONSOLIDACION_TEMATICA.md).

## 2. Metodología de consolidación

### 2.1 Objetivo de la consolidación

La consolidación no busca promediar versiones ni copiar la más nueva. Busca **nivelar hacia arriba**:

- conservar el mejor aporte de cada versión;
- eliminar redundancias;
- corregir contradicciones;
- cerrar vacíos operativos, de seguridad, legales y de consistencia;
- dejar un PRD implementable, auditable y libre de ambigüedad material.

### 2.2 Matriz de decisión usada

Cada aporte histórico se clasificó en una de estas decisiones:

| Decisión | Significado |
|---|---|
| `Adoptar` | El aporte se incorpora prácticamente intacto porque es sólido, claro y consistente. |
| `Adoptar refinado` | El aporte se incorpora, pero reescrito o endurecido para eliminar ambigüedad, riesgo o sobrepromesa. |
| `Fusionar` | El aporte se combina con otros PRD porque ninguno por sí solo era suficiente. |
| `Rechazar` | El aporte no entra al PRD canónico por ser inconsistente, riesgoso, redundante o inferior. |

### 2.3 Criterio de desempate

Ante conflicto entre versiones, gana la opción que mejor cumpla este orden:

1. Legalidad, seguridad y trazabilidad.
2. Coherencia del modelo de negocio.
3. Consistencia operativa y técnica.
4. Claridad documental.
5. Cobertura funcional real.

### 2.4 Decisiones maestras ya resueltas

Estas definiciones quedan cerradas y no son opcionales:

- **Banco**: la conciliación bancaria opera con **API oficial de Banco de Chile** y contingencia manual. No se define web scraping como estrategia oficial del producto.
- **Cambio de arrendatario**: no existe cambio de titular dentro del mismo contrato. El flujo correcto es **término del contrato vigente + contrato nuevo**.
- **Renovaciones**: los contratos **se extienden** mediante nuevos `PeriodoContractual`. No se duplica el contrato ni cambia su identificador.
- **Propiedades vinculadas**: se incluyen como capacidad oficial, pero solo como caso acotado y rigurosamente definido.

### 2.5 Resultado de la relectura exhaustiva

La versión actual del maestro se apoya en una relectura integral de:

- `prd1` a `prd26`;
- [prd.txt](D:/Proyectos/PRDLeaseManager/prd.txt);
- [PRD_UNIFICADO.md](D:/Proyectos/PRDLeaseManager/PRD_UNIFICADO.md);
- [CLAUDE.md](D:/Proyectos/PRDLeaseManager/CLAUDE.md).

La auditoría resultante no solo absorbió aportes, sino que además cerró contradicciones históricas, eliminó sobrepromesas y formalizó reglas que antes aparecían difusas, incompatibles o incompletas.

### 2.6 Resultado de la tercera vuelta lineal

Adicionalmente, se ejecutó una tercera pasada de lectura:

- secuencial;
- lineal;
- `prd1` a `prd26` en orden;
- con registro de deltas por archivo y por bloque.

Esa tercera vuelta permitió:

- detectar micro-reglas que no destacaban en la lectura temática;
- distinguir contenido normativo real de ruido generado por asistentes o truncados;
- reforzar la matriz temática con tensiones más finas;
- profundizar el maestro solo donde la nueva evidencia aportó precisión real.

## 3. Visión del producto

**LeaseManager** es un ERP especializado en administración de arriendos comerciales en Chile. Su propósito es convertir una operación intensiva en planillas, mensajería manual, conciliaciones lentas y decisiones tributarias dispersas en un sistema centralizado, auditable y altamente automatizado.

El sistema debe permitir:

- cálculo exacto de renta mensual en CLP con conversión UF y código de propiedad;
- gestión contractual completa con períodos, extensiones, avisos de término y firma mixta;
- notificaciones configurables por contrato y por día;
- conciliación bancaria exacta sobre API oficial;
- gestión integral de garantías, deudas y repactaciones;
- facturación electrónica y evolución hacia contabilidad inteligente;
- publicación automatizada de propiedades cuando existan integraciones realmente soportadas.

## 4. Principios rectores

### 4.1 Prohibición absoluta de soluciones temporales

Regla inviolable:

- No se aceptan parches, placeholders, TODO/FIXME ni atajos conscientes.
- Si una solución no es correcta, completa y defendible, no entra al producto.
- Cada decisión debe quedar lista para producción desde su primera entrega.

### 4.2 Fuente única de verdad

Toda operación relevante debe quedar anclada al modelo transaccional del sistema:

- contratos;
- períodos;
- pagos mensuales;
- conciliaciones;
- documentos;
- garantías;
- avisos;
- deudas;
- asientos y reportes futuros.

### 4.3 Trazabilidad total

Cada evento sensible debe ser auditable:

- quién ejecutó la acción;
- cuándo;
- contra qué entidad;
- qué cambió;
- por qué cambió;
- si hubo aprobación humana;
- si hubo dato externo involucrado.

### 4.4 IA con supervisión humana

La IA puede:

- sugerir;
- clasificar;
- priorizar;
- resumir;
- detectar anomalías.

La IA no puede:

- alterar contratos por sí sola;
- decidir conciliaciones complejas sin validación humana;
- enviar presentaciones regulatorias finales sin la política de aprobación definida para esa fase.

### 4.5 Integraciones oficiales y defensibles

Cuando exista integración crítica externa:

- se prioriza el canal oficial soportado;
- se documentan condiciones de activación;
- se explicita el modo degradado;
- no se promete automatización total cuando la dependencia externa no está validada.

### 4.6 Reglas de precedencia documental

Para evitar interpretaciones contradictorias, la precedencia interna del documento es:

1. Definiciones canónicas del modelo de dominio.
2. Reglas de negocio definitivas.
3. Flujos operacionales críticos.
4. Integraciones externas y condiciones de activación.
5. Roadmap y evolución futura.

Si un ejemplo, escenario o fase parece contradecir una definición canónica o una regla de negocio:

- prevalece la definición canónica;
- el ejemplo debe interpretarse como ilustrativo, no normativo;
- el roadmap no puede invalidar una regla ya fijada del modelo o del dominio.

### 4.7 Gobernanza del PRD

Para esta versión del maestro, cada bloque del documento cae en una de estas categorías:

- **Normativo**: modelo de dominio, reglas de negocio, controles anti-inconsistencia, límites y políticas de fallback.
- **Operativo**: flujos, criterios de aceptación, roles, alertas, procedimientos manuales permitidos.
- **Condicionado por gate**: integraciones externas y automatizaciones cuya activación depende de readiness externo, compliance, credenciales o validación formal.
- **Evolutivo**: roadmap, capacidades futuras y ampliaciones no vigentes todavía como obligación productiva.

Reglas de lectura:

- lo normativo prevalece sobre lo operativo;
- lo operativo prevalece sobre ejemplos ilustrativos;
- lo condicionado por gate no puede leerse como capacidad activa por defecto;
- lo evolutivo orienta priorización, pero no invalida restricciones activas del dominio.

## 5. Localización, usuarios y KPIs

### 5.1 Localización

- Idioma de producto: español de Chile.
- Formato de fecha: `dd/mm/yyyy`.
- Zona horaria oficial: `America/Santiago`.
- Monedas principales: `CLP` y `UF`.

### 5.2 Roles base del sistema

| Rol | Alcance | Restricciones duras |
|---|---|---|
| `Administrador Global` | Acceso total, configuración, aprobación, cierres, reaperturas, integraciones y resolución de conflictos. | Ninguna funcional relevante. |
| `Contadora` | Lectura sobre información financiera, contractual y documental autorizada. | No modifica operación ni ve secretos. |
| `Socio` | Vista filtrada por sus participaciones y entidades relacionadas. | No opera contratos ni conciliaciones ajenas. |

Además de los roles base:

- el sistema puede soportar roles operativos adicionales creados por el Administrador Global;
- cualquier rol adicional debe derivarse por mínimo privilegio;
- ningún rol personalizado puede superar los límites del Administrador Global.

### 5.3 Personas representativas

- **Andrés, Administrador Global**: necesita automatización, control mensual, alertas y certeza operativa.
- **Carolina, Contadora**: necesita orden, exportabilidad, trazabilidad y consistencia tributaria.
- **Roberto, Socio**: necesita visibilidad filtrada, rendimiento y transparencia sin intervenir la operación.

### 5.4 KPIs de éxito

| KPI | Objetivo |
|---|---|
| Reducción del tiempo administrativo mensual | `-90%` dentro de 6 meses de adopción |
| Tasa de error post-conciliación | `<1%` |
| Tasa de pago puntual | `+15%` respecto de la línea base |
| Carga del dashboard principal | `<2 segundos` con caché |
| Generación de PDF contractual | `<3 segundos` |
| Uptime mensual | `99,5%` |
| Adopción del flujo documental automatizado | `>95%` de nuevos contratos |

## 6. Alcance funcional del producto

LeaseManager cubre estos macrodominios:

1. Datos maestros.
2. Onboarding de arrendatarios.
3. Contratos y períodos contractuales.
4. Cálculo de renta y generación de `PagoMensual`.
5. Notificaciones y comunicaciones.
6. Conciliación bancaria.
7. Garantías.
8. Deudas, repactaciones y cobranza post-contrato.
9. Documentos, firma y notaría.
10. Facturación electrónica y evolución contable.
11. Dashboard operacional y reportes.
12. Publicación inmobiliaria condicionada a APIs disponibles.

## 7. Modelo de dominio y definiciones canónicas

### 7.1 Socio

Entidad que representa a una persona natural con participación patrimonial o societaria.

Campos mínimos:

- `id`
- `nombre`
- `rut`
- `email`
- `telefono`
- `domicilio`
- `nacionalidad`
- `profesion`
- `estado_civil`
- `activo`

Reglas:

- No puede eliminarse si tiene participaciones activas.
- Si deja de participar, puede inactivarse o transferirse su participación mediante wizard controlado.
- Puede ser representante legal si su información está completa.

### 7.2 Empresa

Entidad propietaria o administradora del activo.

Campos mínimos:

- `id`
- `razon_social`
- `rut`
- `domicilio`
- `giro`
- `codigo_actividad_sii`
- `representante_legal_socio_id`
- `estado`

Reglas:

- La suma de participaciones de socios debe ser exactamente `100%`.
- Debe tener al menos una cuenta bancaria operativa para operar.
- Si no tiene propiedades, contratos ni cuentas activas, puede eliminarse.
- Si se disuelve, la transferencia a socios debe preservar contratos, trazabilidad y documentos.

### 7.3 Cuenta bancaria

Cuenta bancaria usada para recaudar arriendos y otros movimientos.

Campos mínimos:

- `id`
- `banco`
- `numero_cuenta`
- `tipo_cuenta`
- `titular_nombre`
- `titular_rut`
- `email_contacto`
- `estado_operativo`

Reglas:

- Una cuenta bancaria puede asociarse a múltiples empresas.
- Una cuenta bancaria soporta como máximo `999` propiedades por la restricción de códigos `001-999`.

### 7.4 Conexión bancaria oficial

Definición canónica de integración bancaria. Reemplaza la noción histórica de credenciales de portal.

Campos mínimos:

- `id`
- `cuenta_bancaria_id`
- `provider = BancoDeChile`
- `client_id`
- `client_secret` o secreto equivalente
- `access_token`
- `refresh_token`
- `scope`
- `expira_en`
- `estado_conexion`
- `ultimo_exito_at`
- `ultimo_error_at`
- `ultimo_error_codigo`
- `ultimo_error_detalle`

Reglas:

- El producto **no** define almacenamiento de usuario/clave de portal bancario como estrategia oficial.
- La validación de conexión es asíncrona y auditable.
- Si la integración oficial no está disponible, la contingencia es manual, no scraping.

Estados de conexión:

- `Verificando`
- `Activa`
- `Pausada`
- `Inactiva`

### 7.5 Propiedad

Unidad inmobiliaria base.

Campos mínimos:

- `id`
- `codigo_propiedad`
- `rol_avaluo`
- `direccion`
- `comuna`
- `region`
- `tipo_inmueble`
- `empresa_propietaria_id` o comunidad de socios
- `representante_comunidad_id` cuando aplique
- `datos_servicios`
- `tiene_gastos_comunes`
- `datos_comercializacion`

Reglas:

- `codigo_propiedad` es un código numérico de tres dígitos entre `001` y `999`.
- El código es único dentro de la cuenta bancaria.
- Puede repetirse entre cuentas distintas.
- Una propiedad no puede pertenecer simultáneamente a empresa y comunidad de socios.
- Una propiedad puede tener como máximo:
  - `1` contrato vigente;
  - `1` contrato futuro.

### 7.6 Propiedad principal y propiedad vinculada

Capacidad oficial para casos como:

- departamento + bodega;
- local + oficina complementaria;
- frente + fondo;
- casa + estacionamiento.

#### Definiciones

- **Propiedad Principal**: propiedad que lidera la vinculación y aporta el código efectivo de conciliación.
- **Propiedad Vinculada**: propiedad complementaria que mantiene su identidad patrimonial, pero comparte cobro contractual con la principal.
- **Código de Conciliación Efectivo**: código que se embebe en el monto a pagar y se usa para conciliación automática. Si existe vinculación, es el código de la propiedad principal.

#### Reglas maestras

- Una vinculación admite exactamente:
  - `1` propiedad principal;
  - `1` propiedad vinculada.
- Ambas deben pertenecer a la misma cuenta bancaria.
- Ambas deben pertenecer al mismo contexto de titularidad y arrendador operativo.
- Ambas deben compartir el mismo contrato vigente.
- Ambas deben compartir:
  - arrendatario;
  - calendario de pago;
  - aviso de término;
  - política de notificaciones;
  - tratamiento de garantía.
- La propiedad vinculada conserva su código estructural para trazabilidad, pero hereda el código efectivo de conciliación.
- Mientras una propiedad esté vinculada a otra, no puede tener un contrato activo independiente.
- Si se requiere separar la pareja durante la vigencia, el sistema debe exigir un proceso explícito de división contractual con efecto desde cierre de mes o mediante nuevos contratos sucesores.

#### Restricción de alcance

Este PRD **no** abre el modelo a contratos multi-propiedad genéricos ilimitados. El caso soportado es:

- una sola propiedad; o
- una pareja `principal + vinculada`.

### 7.7 Arrendatario

Entidad arrendataria persona natural o empresa.

Campos mínimos:

- `id`
- `tipo_arrendatario`
- `email`
- `telefono`
- `domicilio_notificaciones`
- `estado_contacto`
- `whatsapp_bloqueado`
- `score_pago`

Si es persona natural:

- `nombre`
- `apellido`
- `rut`
- `nacionalidad`
- `profesion`
- `estado_civil`

Si es empresa:

- `razon_social`
- `rut_empresa`
- `domicilio_empresa`
- `representante_legal_nombre`
- `representante_legal_rut`

### 7.8 Flujo de onboarding de arrendatarios

El alta de arrendatarios soporta flujo asistido:

1. El administrador registra el email inicial.
2. El sistema envía un formulario externo con expiración.
3. El prospecto completa sus datos.
4. El administrador aprueba o rechaza.
5. El arrendatario queda creado con trazabilidad del origen.

### 7.9 Contrato

Entidad jurídica y operativa central.

Campos mínimos:

- `id`
- `codigo_contrato`
- `arrendatario_id`
- `arrendador_tipo`
- `arrendador_id`
- `fecha_inicio`
- `fecha_fin_vigente`
- `fecha_entrega`
- `dia_pago_mensual`
- `plazo_notificacion_termino_dias`
- `dias_prealerta_admin`
- `estado`
- `tiene_tramos`
- `tiene_gastos_comunes`
- `tipo_inmueble_contratado`
- `giro_comercial`
- `snapshot_representante_legal`

Reglas:

- Su identidad es inmutable.
- Se extiende con `PeriodoContractual`; no se duplica por renovación.
- Puede cubrir:
  - `1` propiedad; o
  - `1` pareja `principal + vinculada`.
- Si cambia el arrendatario, se termina y nace otro contrato.

### 7.10 ContratoPropiedad

Relación explícita entre contrato y propiedad. Debe existir como definición canónica, no como lista ambigua.

Campos mínimos:

- `contrato_id`
- `propiedad_id`
- `rol_en_contrato`
- `porcentaje_distribucion_interna`
- `codigo_conciliacion_efectivo_snapshot`

Reglas:

- `rol_en_contrato` puede ser `Principal` o `Vinculada`.
- Si el contrato cubre solo una propiedad, la distribución interna es `100%`.
- Si cubre una pareja vinculada, la distribución interna debe sumar `100%` y se usa solo para reportes, rentabilidad y contabilidad interna.
- La distribución interna no altera el monto cobrado al arrendatario ni la conciliación bancaria.

### 7.11 PeriodoContractual

Tramo temporal del contrato con base económica definida.

Campos mínimos:

- `id`
- `contrato_id`
- `numero_periodo`
- `fecha_inicio`
- `fecha_fin`
- `monto_base`
- `moneda_base`
- `tipo_periodo`
- `origen_periodo`

Tipos:

- `Inicial`
- `Renovacion`
- `Extension`
- `Tramo`

### 7.12 PagoMensual

Obligación mensual generada para un contrato.

Campos mínimos:

- `id`
- `contrato_id`
- `periodo_contractual_id`
- `mes`
- `anio`
- `monto_calculado_clp`
- `monto_pagado_clp`
- `fecha_vencimiento`
- `fecha_deposito_banco`
- `fecha_deteccion_sistema`
- `estado_pago`
- `dias_mora`
- `codigo_conciliacion_efectivo`

Reglas:

- Si el contrato cubre una pareja vinculada, existe **un** `PagoMensual` por contrato, no uno por propiedad.
- La trazabilidad por propiedad se conserva a través de `ContratoPropiedad`.

Estados de pago soportados:

- `Pendiente`
- `Pagado`
- `Atrasado`
- `EnRepactacion`
- `PagadoViaRepactacion`
- `PagadoPorAcuerdoDeTermino`
- `Condonado`

### 7.13 AjusteContrato

Descuento o recargo aplicable al cálculo mensual.

Campos mínimos:

- `id`
- `contrato_id`
- `tipo_ajuste`
- `monto`
- `moneda`
- `mes_inicio`
- `mes_fin`
- `justificacion`
- `creado_por`

Reglas:

- Se aplica antes de insertar el código de propiedad.
- Nunca puede empujar el monto resultante bajo `CLP 1.000`.

### 7.14 Garantía e historial de garantía

La garantía es un concepto del contrato, no de la propiedad individual.

#### Garantía contractual

Campos mínimos:

- `monto_pactado`
- `monto_recibido`
- `monto_devuelto`
- `estado_garantia`
- `fecha_recepcion`
- `fecha_cierre`

#### HistorialGarantia

Campos mínimos:

- `id`
- `contrato_id`
- `tipo_movimiento`
- `monto_clp`
- `fecha`
- `justificacion`
- `movimiento_origen_id`

Reglas:

- En contratos con propiedades vinculadas, existe una sola garantía por contrato.
- Si una pareja vinculada se separa, la garantía debe cerrarse, redistribuirse o reconstituirse mediante proceso explícito y auditable.

### 7.15 EstadoCuentaArrendatario

Vista unificada de deuda y cumplimiento.

Debe consolidar:

- pagos pendientes;
- pagos atrasados;
- repactaciones activas;
- deuda histórica;
- deuda post-contrato;
- score de pago;
- observaciones relevantes.

Regla de score:

- formato visible: `X% (Y de Z meses)`;
- se excluyen meses sin registro operativo;
- un pago repactado cuenta como cumplido solo si la cuota exigible del mes fue efectivamente cubierta en plazo.

### 7.16 Repactación de deuda

Plan estructurado de pago sobre deuda existente.

Campos mínimos:

- `id`
- `arrendatario_id`
- `contrato_origen_id`
- `deuda_total_original`
- `cantidad_cuotas`
- `monto_cuota`
- `saldo_pendiente`
- `estado`

Reglas:

- La repactación pertenece a la obligación de pago, no reescribe la historia del contrato.
- Los meses originales conservan trazabilidad y estado de origen.

### 7.17 Código de deudor post-contrato

Mecanismo para cobrar deuda residual luego del término del contrato.

Reglas:

- Usa rango exclusivo `900-999`.
- No reemplaza códigos de propiedad activos.
- Persiste aunque el arrendatario celebre contratos nuevos.

### 7.18 Documento contractual y archivo operativo

Documentos relevantes:

- contrato principal;
- anexos;
- cartas de aviso;
- liquidaciones de garantía;
- respaldos de ingresos y gastos;
- comprobantes de notaría;
- XML/PDF tributarios.

Todos los documentos deben almacenar:

- checksum;
- fecha de carga;
- usuario;
- tipo documental;
- entidad asociada;
- permisos de acceso.

## 8. Reglas de negocio definitivas

### 8.1 Propiedad y porcentajes

- La suma de participaciones en empresa debe ser `100%`.
- La suma de participaciones en comunidad de socios debe ser `100%`.
- Si la propiedad pertenece a comunidad, debe existir representante definido dentro de los socios copropietarios.

### 8.2 Reglas contractuales inmutables

- Los contratos solo pueden iniciar el día `1` del mes.
- Los contratos siempre terminan el último día del mes.
- El `dia_pago_mensual` válido está entre `1` y `5`.
- No existe contrato ni tramo con monto inferior a `CLP 1.000`.
- El contrato mantiene su identidad durante toda su vida.
- Las renovaciones agregan períodos; no crean contrato nuevo.
- El contrato futuro solo puede existir si hay aviso de término activo o terminación anticipada ejecutada.

### 8.3 Cálculo de renta mensual

Secuencia canónica:

1. Obtener el `Monto Contractual Bruto` vigente desde `PeriodoContractual`.
2. Convertir a CLP si corresponde, usando UF del día 1 del mes.
3. Aplicar ajustes vigentes.
4. Truncar decimales.
5. Validar mínimo absoluto de `CLP 1.000`.
6. Reemplazar los últimos tres dígitos por el `Código de Conciliación Efectivo`.
7. Persistir el resultado como `monto_calculado_clp`.

### 8.4 Fuente de UF

Cadena oficial:

1. Banco Central.
2. CMF.
3. MiIndicador.

Si todas fallan:

- el sistema levanta alerta crítica;
- se habilita ingreso manual extraordinario con auditoría;
- el valor manual debe quedar con usuario, fecha y motivo.

### 8.5 Fórmula de inserción de código

Ejemplo conceptual:

```text
monto_truncado = 523456
codigo_efectivo = 042
resultado = 523042
```

Reglas:

- Siempre se reemplazan los últimos tres dígitos.
- No se redondea.
- En propiedades vinculadas, se usa el código de la principal.

### 8.6 Reglas de propiedades vinculadas

- Una vinculación sirve para activos comercialmente complementarios, no para portafolios abiertos.
- La pareja vinculada comparte cobro, garantía, avisos y calendario.
- El arrendatario paga un monto único por contrato.
- La conciliación automática observa un único monto esperado y un único código efectivo.
- Los reportes internos pueden distribuir ingresos entre principal y vinculada según `porcentaje_distribucion_interna`.
- Si se requiere separar la pareja, debe ejecutarse un proceso explícito de reconfiguración contractual.

### 8.7 Notificaciones

Configuración base sugerida:

- días `1, 3, 5, 10, 15, 20, 25`;
- canales configurables por día;
- hora operativa de WhatsApp entre `08:00` y `21:00`.

Reglas:

- Cada contrato puede personalizar días y canales.
- Debe existir al menos un canal operativo para comunicación contractual.
- Email es el canal base recomendado y debe mantenerse disponible.
- Si WhatsApp falla por bloqueo o error definitivo, el sistema debe:
  - registrar el evento;
  - marcar el contacto;
  - alertar al administrador;
  - continuar por email cuando exista.

### 8.8 Conciliación bancaria

#### Política oficial

- Solo Banco de Chile API oficial.
- Sin scraping como estrategia canónica.
- Sin credenciales de portal como modelo oficial.

#### Modos de operación

- **Automático exacto**: si `monto + código efectivo` calzan exactamente.
- **Asistido por IA**: si hay alta probabilidad pero no exactitud.
- **Manual**: si la API no entrega datos suficientes, falla o el caso es ambiguo.

#### Reglas

- La IA sugiere; el administrador decide.
- No se debe autoasignar un pago ambiguo a un contrato distinto por conveniencia operativa.
- Los ingresos sin match quedan como `IngresoDesconocido`.

### 8.9 Fechas de pago y trazabilidad temporal

Para eliminar ambigüedad, el sistema debe guardar dos fechas:

- `fecha_deposito_banco`: fecha informada por la API bancaria cuando exista.
- `fecha_deteccion_sistema`: timestamp en que LeaseManager la conoció.

Uso correcto:

- mora y puntualidad: `fecha_deposito_banco` si existe y es confiable;
- auditoría de ingestión y operación: `fecha_deteccion_sistema`.

### 8.10 Garantías

- La garantía se pacta a nivel de contrato.
- No genera intereses ni reajustes.
- Su estado se calcula a partir del historial.
- Puede haber recepción, devolución total, devolución parcial, retención parcial o retención total.
- El flujo normal es:
  - crear contrato;
  - recibir garantía;
  - entregar llaves.

### 8.11 Cambio de arrendatario

Política definitiva:

- No existe cambio de arrendatario dentro del mismo contrato.
- Debe terminar el contrato anterior y crearse uno nuevo.
- Las deudas y trazabilidad histórica permanecen en el contrato original.
- La garantía del contrato anterior debe liquidarse o regularizarse antes de cerrar el flujo.

### 8.12 Contratos retroactivos

- Se permiten sin límite temporal, siempre respetando inicio en día 1.
- El sistema no genera operaciones retroactivas ficticias para meses ya pasados.
- Si el contrato se crea después del día 5 del mes en curso, debe advertirse que ese mes puede requerir notificación manual.
- Los cobros futuros de contratos retroactivos siguen usando la regla general de cálculo del mes correspondiente; se rechaza como regla canónica usar el “valor UF más alto histórico” del período completo del contrato retroactivo.

### 8.13 Avisos de término

- Deben registrarse con precisión temporal auditable.
- Bloquean la renovación automática si están vigentes.
- Habilitan contrato futuro.
- Su cancelación puede exigir primero la cancelación del contrato futuro asociado.

### 8.14 Cierre de mes

- El cierre mensual ocurre automáticamente al final del período definido.
- Los movimientos posteriores no alteran meses cerrados.
- La reapertura solo la puede ejecutar el Administrador Global con justificación auditada.

### 8.15 Invariantes del dominio

Estas reglas deben cumplirse siempre:

- una propiedad no puede pertenecer simultáneamente a empresa y comunidad de socios;
- toda empresa debe sumar `100%` de participación;
- toda comunidad propietaria debe sumar `100%` de participación;
- una propiedad solo puede tener `1` contrato vigente;
- una propiedad solo puede tener `1` contrato futuro;
- una propiedad vinculada no puede tener contrato activo independiente;
- un contrato solo puede cubrir `1` propiedad o `1` pareja `principal + vinculada`;
- una garantía pertenece al contrato, no a la propiedad individual;
- un `PagoMensual` pertenece al contrato y nunca puede quedar “duplicado” por propiedad vinculada;
- un contrato renovado conserva identidad;
- un cambio de arrendatario siempre genera contrato nuevo;
- el código de conciliación efectivo de una pareja vinculada siempre es el de la propiedad principal.

### 8.16 Fallbacks permitidos y prohibidos

Fallbacks permitidos:

- UF: Banco Central -> CMF -> MiIndicador -> carga manual auditada;
- conciliación bancaria: API oficial -> operación manual;
- mensajería: WhatsApp disponible -> email -> alerta al administrador si ambos fallan;
- caché: Redis -> modo degradado sin caché;
- publicación inmobiliaria: automatización por API -> checklist/manual asistido.

Fallbacks prohibidos como regla canónica:

- API bancaria -> scraping de portales bancarios;
- documento incompleto -> “corregir después”;
- regla ambigua -> decisión implícita sin registrar;
- presentación regulatoria crítica -> ejecución autónoma por IA sin política explícita de aprobación.

### 8.17 Controles anti-inconsistencia

El sistema debe impedir o bloquear explícitamente:

- creación de contrato futuro sin aviso de término o terminación anticipada;
- cancelación de aviso de término si existe contrato futuro no revertido;
- eliminación de socio con participaciones activas;
- eliminación de empresa con contratos, propiedades o cuentas operativas activas;
- cambios retroactivos silenciosos sobre meses ya cerrados;
- cambios estructurales en propiedades vinculadas sin proceso de división contractual;
- generación de montos por debajo del mínimo de `CLP 1.000`;
- asignación automática de pagos ambiguos;
- modificación de identidad de contrato durante renovación;
- acceso de roles no autorizados a secretos, trazas sensibles o decisiones de cierre.

### 8.18 Transiciones de estado críticas

Transiciones mínimas que deben respetarse:

- **Contrato**:
  - `PendienteActivacion -> Vigente`
  - `Vigente -> TerminadoAnticipadamente`
  - `Vigente -> Finalizado`
  - `Vigente -> Cancelado` solo si no produjo efectos operativos irreversibles
- **PagoMensual**:
  - `Pendiente -> Pagado`
  - `Pendiente -> Atrasado`
  - `Atrasado -> EnRepactacion`
  - `EnRepactacion -> PagadoViaRepactacion`
  - `Pendiente/Atrasado -> PagadoPorAcuerdoDeTermino` cuando corresponda
- **Aviso de término**:
  - `Borrador -> Registrado`
  - `Registrado -> Cancelado` solo si no existe contrato futuro activo sin revertir
- **Conexión bancaria oficial**:
  - `Verificando -> Activa`
  - `Verificando -> Pausada`
  - `Activa -> Pausada`
  - `Pausada -> Activa`
  - `Pausada/Activa -> Inactiva`

Regla general:

- toda transición crítica debe registrar actor, timestamp, motivo y entidad afectada.

### 8.19 Políticas de excepción y resolución manual

Se permite resolución manual solo cuando:

- falla una integración oficial crítica;
- un caso no puede resolverse automáticamente sin riesgo de error;
- la regla de negocio exige intervención humana;
- existe un conflicto contractual o documental con impacto jurídico.

Toda excepción manual debe dejar:

- motivo explícito;
- usuario responsable;
- datos afectados;
- criterio aplicado;
- evidencia documental si corresponde;
- marca visible para auditoría posterior.

## 9. Flujos operacionales críticos

### 9.1 Alta de arrendatario

1. Administrador registra email inicial.
2. Sistema envía formulario.
3. Prospecto completa datos.
4. Administrador revisa.
5. Se aprueba o rechaza.
6. Si se aprueba, queda habilitado para contratación.

### 9.2 Creación de contrato

1. Seleccionar propiedad o pareja vinculada.
2. Validar propietario, cuenta bancaria y reglas de elegibilidad.
3. Seleccionar arrendatario.
4. Configurar monto, moneda, períodos, reajuste, garantía, notificaciones y codeudores.
5. Generar vista previa de períodos y cobros.
6. Confirmar contrato.

### 9.3 Generación documental y firma mixta

1. Generar documento desde plantilla `DOCX`.
2. Convertir a `PDF`.
3. Enviar para revisión del arrendatario.
4. Aplicar firma electrónica del arrendador.
5. Derivar a notaría.
6. Registrar recepción del documento final firmado.

### 9.4 Ciclo mensual

1. Obtener UF y datos externos necesarios.
2. Generar `PagoMensual`.
3. Emitir factura electrónica cuando corresponda.
4. Enviar notificaciones.
5. Conciliar movimientos bancarios.
6. Actualizar dashboard, score y estado de cuenta.

### 9.5 Terminación anticipada

1. Registrar fecha efectiva y causal.
2. Consolidar deuda y último mes.
3. Definir tratamiento de garantía.
4. Emitir documentación de término.
5. Cerrar contrato y, si corresponde, habilitar contrato futuro o deuda residual.

### 9.6 Gestión de propiedades vinculadas

1. Definir propiedad principal.
2. Asociar propiedad vinculada elegible.
3. Configurar distribución interna.
4. Generar contrato único.
5. Cobrar y conciliar con código efectivo único.
6. Reportar resultados por propiedad sin partir el cobro.

### 9.7 Contingencia bancaria manual

Si la API oficial no permite operar:

1. El sistema marca la cuenta en estado degradado.
2. Se notifica al administrador.
3. Se habilita carga y asignación manual de movimientos.
4. Toda asignación manual queda con motivo y trazabilidad.

## 10. Integraciones externas y condiciones de activación

### 10.1 Banco de Chile API

Uso:

- obtener movimientos;
- conciliar pagos;
- validar conectividad;
- sincronizar saldos.

Condición:

- integración oficial activa y autorizada.

Gate estricto:

- **Entrada**:
  - credenciales oficiales válidas;
  - conectividad saludable;
  - scopes y permisos suficientes;
  - cuenta bancaria marcada como operativa.
- **Suspensión**:
  - rechazo persistente de autenticación;
  - indisponibilidad sostenida del proveedor;
  - revocación o expiración no recuperada de credenciales.
- **Salida de gate**:
  - restauración verificada de conectividad;
  - validación manual o automática de salud;
  - primer ciclo exitoso de sincronización.

Fallback:

- operación manual.

Fallback prohibido:

- scraping de portal bancario;
- reutilización de credenciales no oficiales;
- conciliación automática inferida sin datos suficientes.

### 10.2 Proveedores UF

Uso:

- cálculo de renta;
- reajustes;
- validaciones de contratos en UF.

Cadena:

- Banco Central;
- CMF;
- MiIndicador;
- contingencia manual auditada.

Gate estricto:

- **Entrada**:
  - proveedor accesible;
  - dato disponible para la fecha requerida;
  - formato validado.
- **Suspensión**:
  - dato ausente o inconsistente;
  - falla de cadena completa.
- **Salida de gate**:
  - recuperación del proveedor; o
  - carga manual auditada aprobada.

### 10.3 Gmail API

Uso:

- notificaciones;
- avisos;
- documentos;
- facturas y comunicaciones formales.

Modos soportados:

- Gmail por empresa;
- Gmail por cuenta bancaria.

Lógica:

- si la empresa tiene Gmail propio, se usa ese;
- si no, se usa el de la cuenta bancaria;
- si falta configuración, se alerta al administrador.

Gate estricto:

- **Entrada**:
  - OAuth válido;
  - remitente configurado;
  - prueba de envío satisfactoria.
- **Suspensión**:
  - token expirado sin refresco;
  - cuenta desconectada;
  - rechazo del proveedor.
- **Salida de gate**:
  - refresco exitoso;
  - nueva prueba de envío correcta.

### 10.4 Twilio WhatsApp Business

Uso:

- recordatorios;
- avisos operacionales;
- alertas puntuales.

Condiciones:

- templates aprobados;
- horario permitido;
- número válido y canal no bloqueado.

Gate estricto:

- **Entrada**:
  - template aprobado;
  - canal habilitado;
  - número validado;
  - ventana horaria permitida.
- **Suspensión**:
  - error definitivo de canal;
  - número bloqueado;
  - template rechazado o deshabilitado.
- **Salida de gate**:
  - rehabilitación documentada;
  - nueva prueba exitosa.

Fallback permitido:

- email;
- alerta al administrador.

### 10.5 API SII

Uso:

- facturación electrónica;
- evolución futura a presentaciones tributarias.

Política:

- integración directa, sin intermediarios obligatorios.
- emisión automática solo cuando el arrendador sea una empresa habilitada para facturar.
- aprobación humana obligatoria por defecto en presentaciones tributarias de mayor sensibilidad hasta que exista validación regulatoria y operativa suficiente para un modo más autónomo.

Gate estricto:

- **Entrada**:
  - empresa habilitada;
  - certificado vigente;
  - folios disponibles cuando aplique;
  - ambiente y credenciales validados;
  - pruebas de emisión exitosas para el flujo activo.
- **Suspensión**:
  - certificado vencido o inválido;
  - error sistemático de envío;
  - cambio normativo no validado;
  - ausencia de readiness formal para automatización extendida.
- **Salida de gate**:
  - prueba de cumplimiento exitosa;
  - credenciales o certificado regularizados;
  - aprobación explícita de readiness.

Fallback permitido:

- generación de borrador;
- revisión humana;
- operación manual controlada.

### 10.6 Yapo y Portal Inmobiliario

Uso futuro:

- publicación;
- actualización;
- despublicación;
- consolidación de consultas.

Condición obligatoria:

- existencia de API o integración formal realmente disponible y jurídicamente utilizable.

Gate estricto:

- **Entrada**:
  - API pública o integración formal vigente;
  - términos de uso compatibles;
  - mapeo de campos completo;
  - flujo de alta, actualización y baja probado.
- **Suspensión**:
  - ausencia de API viable;
  - cambio unilateral de términos;
  - rechazo operativo o legal del canal.
- **Salida de gate**:
  - nueva validación técnica y jurídica;
  - prueba end-to-end satisfactoria.

Si no existe:

- el producto no promete automatización total;
- puede ofrecer checklist y asistencia manual.

### 10.7 IA y servicios de lenguaje

Uso permitido:

- conciliación asistida;
- clasificación documental;
- resúmenes;
- análisis ejecutivo;
- futuro asistente conversacional.

Condiciones:

- control de permisos;
- auditoría de prompts y respuestas sensibles;
- ausencia de ejecución autónoma sobre operaciones críticas.

Gate estricto:

- **Entrada**:
  - políticas de permisos definidas;
  - logging habilitado;
  - prompts y salidas clasificadas por criticidad;
  - límites de acción definidos por caso de uso.
- **Suspensión**:
  - salida no confiable o no explicable;
  - fuga de contexto sensible;
  - intento de ejecución fuera del perímetro permitido.
- **Salida de gate**:
  - remediación verificada;
  - nueva validación del caso de uso;
  - reautorización del flujo correspondiente.

## 11. Requisitos de seguridad, resiliencia y auditoría

### 11.1 Seguridad

- Todo secreto debe almacenarse cifrado.
- Los accesos deben ser por HTTPS y sesiones seguras.
- Debe existir separación clara entre datos operativos y secretos.
- La Contadora y el Socio no acceden a secretos de integración.
- Deben existir límites de tasa, controles de acceso y registros de intento fallido.

### 11.2 Auditoría

Debe existir `AuditLog` para:

- contratos;
- avisos;
- reaperturas de mes;
- conciliaciones manuales;
- repactaciones;
- cambios de configuración;
- documentos sensibles;
- integraciones externas.

### 11.3 Resiliencia

- Si falla caché, el sistema sigue operando en modo degradado.
- Si falla una integración externa, el sistema debe aislar el fallo y continuar con lo demás cuando sea posible.
- Un error en una propiedad o contrato no debe bloquear el procesamiento masivo completo.

### 11.4 Backups y continuidad

- Backups incrementales diarios.
- Backups completos semanales.
- Objetivo RPO: `24 horas`.
- Objetivo RTO: `4 horas`.

### 11.5 Observabilidad

Debe existir monitoreo sobre:

- colas y tareas;
- fallos de integración;
- bloqueos WhatsApp;
- tiempos de cálculo;
- errores documentales;
- degradación del dashboard;
- disponibilidad general.

## 12. Requisitos técnicos y de UX

### 12.1 Stack de referencia

| Capa | Tecnología |
|---|---|
| Backend | Django 5 + Django Ninja |
| Base de datos | PostgreSQL 16 + pgvector |
| Async | Redis + Celery |
| Frontend | React 18 + TypeScript + Vite |
| Estado | TanStack Query + Zustand |
| UI | shadcn/ui + Tailwind CSS |
| Documentos | python-docx-template |
| Email | Gmail API |
| Mensajería | Twilio WhatsApp Business |

### 12.2 UX obligatoria

- La operación mensual crítica debe ser clara y rápida.
- Las acciones irreversibles deben pedir confirmación.
- Las decisiones complejas deben mostrar impacto antes de ejecutar.
- El dashboard debe ser configurable por rol y necesidades operativas.
- Los errores deben ser accionables, no crípticos.

### 12.3 Rendimiento mínimo esperado

- Dashboard principal con caché: `<2 segundos`.
- Generación de documento: `<3 segundos`.
- Respuesta de acciones frecuentes: `<1 segundo` cuando no dependan de integración externa.

### 12.4 Decisiones técnicas congeladas

Para evitar deriva por herencia de versiones históricas:

- la capa API de referencia queda en `Django Ninja` sobre `Django 5`;
- el motor asíncrono de referencia queda en `Redis + Celery`;
- las menciones históricas a `Django REST Framework` como interfaz principal o a `Django Background Tasks` como motor base quedan tratadas como alternativas descartadas para este PRD canónico;
- `Web Workers` pueden usarse como técnica de UX cuando agreguen valor, pero no son una dependencia normativa del producto.

## 13. Roadmap maestro

### Fase 1. Núcleo operativo

- CRUD completos con validaciones duras.
- Modelo contractual definitivo con períodos.
- Cálculo mensual con código.
- Notificaciones configurables.
- Conciliación API exacta.
- Garantías.
- Dashboard inicial.
- Flujo de arrendatario por formulario.

### Fase 2. Inteligencia operacional

- IA para sugerencias de conciliación.
- Documentación contractual completa.
- Firma mixta y notaría.
- Bloqueos WhatsApp y recuperación.
- Score de pago y estado de cuenta.

### Fase 3. Gestión avanzada de deuda y portales

- Repactaciones.
- Código de deudor post-contrato.
- Portal de socios.
- Publicación inmobiliaria si las APIs lo permiten.

### Fase 4. IA conversacional y analítica

- Asistente conversacional de consulta.
- Analítica predictiva de morosidad y vencimientos.
- Resúmenes ejecutivos y exploración semántica.

### Fase 5. Contabilidad inteligente

- Motor contable integrado.
- Preparación automatizada de obligaciones tributarias.
- Aprobación humana obligatoria por defecto para presentaciones críticas.
- Evolución a automatización más profunda solo con validación regulatoria explícita.

## 14. Fuera de alcance

Fuera de alcance del PRD canónico, salvo futura decisión explícita:

- web scraping bancario como estrategia oficial;
- contratos multi-propiedad abiertos más allá de `principal + vinculada`;
- cambios de arrendatario sin término de contrato;
- ejecución autónoma de acciones sensibles por IA;
- publicación automática en portales sin integración formal validada;
- reemplazo de aprobación humana en presentaciones regulatorias críticas por defecto.

## 15. Criterios de aceptación y validación

### 15.1 Criterios globales

Toda funcionalidad aceptada debe:

- funcionar en casos normales y excepcionales previsibles;
- manejar errores relevantes;
- ser auditable;
- ser coherente con el modelo de dominio;
- estar documentada;
- ser consistente con seguridad y permisos.

### 15.2 Escenarios mínimos de validación

1. Contrato estándar de una propiedad.
2. Contrato con propiedad principal y vinculada.
3. Renovación automática.
4. Término y contrato nuevo por cambio de arrendatario.
5. Contrato retroactivo.
6. Falla de API bancaria con contingencia manual.
7. Garantía completa, parcial, devolución y retención.
8. Aviso de término con contrato futuro.
9. Repactación activa y score de pago.
10. Bloqueo WhatsApp y fallback de comunicación.

### 15.3 Aceptación por subsistema

| Subsistema | Debe quedar aceptado si... |
|---|---|
| Contratos y períodos | no permite renovar duplicando contrato, mantiene identidad y respeta fechas válidas |
| Propiedades vinculadas | opera solo como `principal + vinculada`, con un cobro único y trazabilidad por propiedad |
| Conciliación bancaria | distingue exacto, asistido y manual sin asignaciones ambiguas |
| Garantías | conserva un historial completo y coherente con el contrato |
| Deuda y repactación | separa deuda histórica, deuda activa y deuda post-contrato sin reescribir historia |
| Notificaciones | respeta configuración por contrato/día/canal y fallback permitido |
| Documentos y notaría | genera, almacena y traza cada documento crítico y su estado |
| SII | solo opera cuando el gate de readiness está abierto y deja trazabilidad de aprobación |
| Marketing | no se activa sin gate técnico-jurídico abierto |
| Seguridad y resiliencia | bloquea accesos indebidos, registra eventos sensibles y opera en degradado controlado |

## 16. Apéndice A - Fórmulas y límites

### 16.1 Fórmula de monto mensual

```text
monto_base_periodo
-> conversión a CLP si corresponde
-> aplicar ajustes vigentes
-> truncar decimales
-> validar mínimo CLP 1.000
-> reemplazar últimos 3 dígitos por código de conciliación efectivo
-> resultado = monto_calculado_clp
```

### 16.2 Límites operativos

| Recurso | Límite |
|---|---|
| Propiedades por cuenta bancaria | 999 |
| Códigos de propiedad | 001-999 por cuenta |
| Propiedades por vinculación oficial | 2 |
| Contratos futuros por propiedad o pareja vinculada | 1 |
| Codeudores por contrato | 3 |
| Días de notificación | configurables, con base sugerida 1/3/5/10/15/20/25 |

## 17. Apéndice B - Configuración externa requerida

Variables e insumos externos esperados:

- base de datos;
- secretos Django;
- Redis/Celery;
- credenciales Banco de Chile API;
- Gmail API;
- proveedores UF;
- SII;
- Twilio;
- claves de IA;
- almacenamiento seguro;
- `TZ=America/Santiago`.

## 18. Apéndice C - Trazabilidad por versión

| PRD | Aporte principal absorbido | Decisión | Resolución canónica |
|---|---|---|---|
| `prd1` | Base del dominio, cálculo de renta con UF y código, riesgos y NFR iniciales. | `Fusionar` | Se conservó el núcleo funcional; se descartó scraping-first como postura oficial. |
| `prd2` | Mayor precisión en inmutabilidad contractual, categorías de movimiento y fallback UF. | `Adoptar refinado` | Se absorbió la precisión operativa, reemplazando credenciales de portal por integración oficial. |
| `prd3` | Mejor granularidad en estados de garantía y movimientos de retención. | `Fusionar` | Se integró al modelo definitivo de garantía e historial. |
| `prd4` | Prioridad de API bancaria sobre scraping, historial de garantía y avisos de término más robustos. | `Adoptar refinado` | Se mantuvo la prioridad API y la trazabilidad; se eliminó el fallback por scraping. |
| `prd5` | Repactación, fases más claras y robustecimiento operacional. | `Fusionar` | Se absorbió la repactación y el enfoque por fases. |
| `prd6` | Modo degradado, aislamiento de fallos y diseño más resiliente. | `Fusionar` | Se integró en resiliencia y observabilidad. |
| `prd7` | Madurez incremental en conciliación y separación de responsabilidades operativas. | `Fusionar` | Se utilizó como refuerzo de consistencia operacional. |
| `prd8` | Manejo de asignaciones tardías y refinamientos sobre cierre y trazabilidad. | `Fusionar` | Se incorporó al cierre de mes y auditoría. |
| `prd9` | Mayor madurez de alertas, mensajería y tratamiento de fallos. | `Fusionar` | Se absorbió selectivamente en notificaciones y alertas. |
| `prd10` | Notificaciones muy configurables, auditoría más rica y endurecimiento de reglas de contrato. | `Adoptar refinado` | Se mantuvo la flexibilidad por contrato/día; se rechazó scraping y reintentos indefinidos poco defendibles. |
| `prd11` | Reorganización por capacidades y primera cadena lógica de dependencias. | `Fusionar` | Se aprovechó para ordenar el PRD canónico. |
| `prd12` | Enfoque más limpio de fases, dependencias y degradación. | `Fusionar` | Se usó para clarificar MVP y evolución. |
| `prd13` | Snapshot de representante legal, reglas duras de monto mínimo y precisión de propiedad/cuenta. | `Adoptar refinado` | Se incorporó como parte central del modelo definitivo. |
| `prd14` | Usuarios sin límite rígido y RBAC más flexible. | `Adoptar refinado` | Se mantuvieron roles base con capacidad de roles adicionales por mínimo privilegio. |
| `prd15` | Mayor completitud en límites, decisiones de diseño y anexos de referencia. | `Fusionar` | Se absorbió en apéndices y límites operativos. |
| `prd16` | Consolidación madura de NFR, fórmulas y decisiones estructurales. | `Fusionar` | Se integró como soporte del endurecimiento documental. |
| `prd17` | Estructura formal de generación documental y flujo contractual más completo. | `Adoptar` | Se incorporó al flujo de documentos y firma. |
| `prd18` | Refinamiento del flujo documental y continuidad del modelo maduro. | `Fusionar` | Se consolidó con `prd17` y posteriores. |
| `prd19` | Estabilidad del modelo y mejoras incrementales en reglas definitivas. | `Fusionar` | Se absorbió donde reforzaba consistencia. |
| `prd20` | Bloqueos WhatsApp, timestamps finos, riesgos y mitigaciones más realistas. | `Adoptar refinado` | Se integró en comunicaciones, auditoría y riesgos. |
| `prd21` | Onboarding de arrendatarios por formulario, validación asíncrona y regla fuerte de cambio de arrendatario. | `Adoptar refinado` | Se absorbió el flujo de onboarding y el criterio de contrato nuevo; se descartó credencial de portal. |
| `prd22` | Estabilización del modelo maduro con menos ruido estructural. | `Fusionar` | Sirvió como apoyo para consolidación, sin introducir una línea nueva dominante. |
| `prd23` | Snapshot legal más fuerte, control de conflictos con contratos futuros y avisos retroactivos. | `Adoptar` | Se incorporó a contratos, avisos y control de conflictos. |
| `prd24` | Personas, historias de usuario, KPIs, fuera de alcance, UX, NFR y plan de migración. | `Adoptar` | Se absorbió la estructura de producto y medición más madura. |
| `prd25` | Principios fundamentales, clarificación radical de continuidad contractual y propiedades vinculadas. | `Adoptar refinado` | Se mantuvo la idea de vinculación, pero se cerró a `principal + vinculada` y se eliminó lenguaje de “ya implementado” y 1:N abierto. |
| `prd26` | Renombre LeaseManager, cadena UF Banco Central/CMF/MiIndicador, firma mixta, marketing automatizado y visión IA avanzada. | `Adoptar refinado` | Se integró la visión final, condicionando marketing a APIs reales y moderando automatización regulatoria a un modelo aprobable. |

## 19. Apéndice D - Documentos de apoyo considerados

| Documento | Rol en la consolidación |
|---|---|
| `prd.txt` | Metodología de unificación y criterio de auditoría. |
| `PRD_UNIFICADO.md` | Intento previo útil como base de amplitud funcional, corregido por contradicciones y sobrepromesas. |
| `CLAUDE.md` | Resumen operativo del proyecto, stack y reglas maestras del repositorio. |

## 20. Apéndice E - Matriz resumida de decisiones canónicas

| Tema | Decisión resumida | Gate o restricción principal |
|---|---|---|
| Banco | API oficial + contingencia manual | prohibido scraping como estrategia oficial |
| Contratos | se extienden, no se duplican | identidad contractual inmutable |
| Cambio de arrendatario | término + contrato nuevo | prohibido cambiar titular en contrato vigente |
| Contrato futuro | máximo uno y condicionado | requiere aviso o terminación válida |
| Propiedades vinculadas | `1 principal + 1 vinculada` | prohibido multi-propiedad abierto |
| Código de propiedad | `001-999` por cuenta | código efectivo de vinculada = principal |
| Garantía | contractual, no por propiedad | una sola garantía por contrato |
| Notificaciones | configurables por contrato/día/canal | fallback solo por canales permitidos |
| SII | integración directa por fases | readiness y aprobación según criticidad |
| Marketing | solo con API viable | si no hay gate abierto, solo checklist/manual |
| IA | sugiere, no decide sola en lo crítico | permisos, logging y límites estrictos |

## 21. Apéndice F - Glosario mínimo

| Término | Definición |
|---|---|
| `Código de Conciliación Efectivo` | código de 3 dígitos embebido en el monto final para identificación bancaria |
| `Propiedad Principal` | propiedad que lidera la vinculación y aporta el código efectivo |
| `Propiedad Vinculada` | propiedad complementaria que comparte cobro contractual con la principal |
| `ContratoPropiedad` | relación explícita entre contrato y propiedad, con rol y distribución interna |
| `PeriodoContractual` | tramo temporal del contrato con base económica específica |
| `PagoMensual` | obligación mensual generada a nivel de contrato |
| `Gate` | condición formal de activación, suspensión y salida para una integración o automatización |
| `Fallback permitido` | alternativa controlada autorizada por el PRD cuando falla el flujo principal |
| `Fallback prohibido` | salida no aceptada por el PRD aunque sea técnicamente posible |
| `Readiness` | condición técnica, operativa y normativa mínima para activar una capacidad |


