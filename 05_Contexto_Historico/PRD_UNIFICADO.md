# PRD MAESTRO - LeaseManager v1.0
## 1. VISION Y PROPOSITO
**LeaseManager**: ERP inmobiliario integral con IA para arriendos comerciales en Chile. Hasta 999 propiedades/cuenta bancaria.
### Propuesta de Valor
- Automatizacion total gestion arriendos comerciales
- Centralizacion datos (fuente unica de verdad)
- Contabilidad integrada con IA regulatoria chilena
- Conciliacion bancaria inteligente (API Banco de Chile OAuth2)
- Marketing inmobiliario automatizado (Yapo, Portal Inmobiliario)
- Cumplimiento SII 100% garantizado
- Generacion automatica documentos legales PDF
### Usuarios
| Rol | Acceso | Capacidades Especiales |
|-----|--------|------------------------|
| Administrador Global | Completo | Crear ajustes, resolver conflictos, ver credenciales, asignar meses cerrados |
| Contadora | Solo lectura contable | Exportar info fiscal, NO ve credenciales |
| Socio Inversionista | Vista filtrada por RUT | Auto-registro con validacion, dashboard personal (~15 max) |
## 2. PRINCIPIO FUNDAMENTAL INVIOLABLE
```
PROHIBIDO: Soluciones temporales, parches, TODO/FIXME, codigo placeholder
OBLIGATORIO: Codigo production-ready desde commit 1, sin excepciones
```
**Commits:** Frecuentes, descriptivos: QUE cambio, POR QUE, COMO afecta.
## 2.1 PERSONAS DE USUARIO
**Andres (Admin, 52a):** Gestiona +100 propiedades. Experto negocio, no tech. Dolor: "Pierdo horas en tareas repetitivas, calculos UF con errores, perseguir morosos." Necesita: automatizacion total, control centralizado.
**Carolina (Contadora, 45a):** Servicios externos. Dolor: "Info desordenada con errores." Necesita: solo lectura, exportar reportes limpios. Con IA Contable Fase 5 → rol auditoria anual.
**Roberto (Socio, 48a):** Inversionista, no participa gestion. Dolor: "Sin visibilidad de inversiones." Necesita: ver SUS propiedades/empresas cuando quiera.
## 2.2 KPIs
| Metrica | Objetivo | | Metrica | Objetivo |
|---------|----------|---|---------|----------|
| Reduccion tiempo gestion | 90% (6m) | | Uptime | 99.5% mensual |
| Tasa error calculos | <1% inmediato | | Carga Dashboard | <2s (cache) |
| Aumento pago puntual | +15% (6m) | | Generacion PDF | <3s |
| Tiempo arrendar | -50% | | Analisis IA/transaccion | <3s |
| Ahorro contable | 95% (IA) | | Adopcion PDF | 95% contratos |
## 3. MODELO DE DATOS CORE
### 3.1 Entidades Principales
```
SOCIOS: nombre(req), rut(unico,mod11), email(unico), telefono(+56XXXXXXXXX), domicilio(req cartas), nacionalidad, profesion, estado_civil (todos req para ser rep.legal)
• No eliminables con participaciones activas → Wizard transferencia
• Participacion activa = socio_id existe en tabla Empresas o Propiedades(comunidades)
• Puede tener 100% en multiples empresas
• AUTO-REGISTRO: email en BD → crear cuenta → acceso filtrado participaciones

EMPRESAS: razon_social(req), rut(unico,mod11), giro, codigo_actividad_sii, representante_legal→FK Socio(req,snapshot en contratos), participaciones[{socio_id,porcentaje}]=100%, cuenta_bancaria→FK(req,validada async), gmail_configurado(opc)
• Sin propiedades/contratos/cuentas → eliminacion directa
• Disolucion → transfiere propiedades a socios segun participacion

PROPIEDADES: codigo(001-899,unico/cuenta,inmutable), propietario→Empresa|Comunidad Socios(=100%,req rep.legal entre socios), direccion, comuna, region, tipo_inmueble, rol_avaluo(SII), descripcion_comercial, fotos[](max20,JPG/PNG,5MB), amenidades[], datos_servicios:{agua,luz,gas}, superficie_m2, ano_construccion, precio_publicacion, descripcion_publicacion
• Max 1 contrato vigente + 1 futuro por propiedad
• Contrato futuro SOLO despues de registrar aviso termino

ARRENDATARIOS: tipo:'empresa'|'persona_natural'
• Empresa: rut_empresa, razon_social, representante_legal, giro
• Persona: rut, nombre, profesion, estado_civil
• email(req), telefono(+56X), domicilio(req cartas), score_pago:"X%(Y de Z meses)", whatsapp_bloqueado:bool
• FLUJO: Admin ingresa email → Sistema envia formulario(link 7dias) → Prospecto completa → Admin aprueba/rechaza → Creado en BD

CONTRATOS: id_inmutable(UUID), propiedades[]→FK[](1:N), arrendatario→FK, arrendador→Empresa|Socio, fecha_inicio(dia1,estricto), fecha_fin(ultimo dia,auto), fecha_entrega(puede diferir inicio), monto_uf(4dec), porcentaje_reajuste, periodicidad_reajuste, dia_pago(1-5,nunca31), dias_preaviso, dias_prealerta_admin, garantia_monto_uf, garantia_estado, tipo_inmueble:'habitacional'|'comercial', giro_comercial(auto'Habitacional'|manual), tiene_gastos_comunes:bool, tiene_tramos:bool, snapshot_representante:{nombre,rut,domicilio,nacionalidad,profesion,estado_civil,fecha}
• Se EXTIENDEN con periodos, NUNCA duplican
• Retroactivos permitidos sin limite (alerta si crea despues dia5: "sin notifs auto este mes")
• Cambio arrendatario: NO existe → terminar y crear nuevo
• Contrato futuro: SOLO si existe aviso termino registrado

CODEUDORES_SOLIDARIOS: contrato→FK, min0 max3, datos_snapshot:{nombre,rut,domicilio,profesion,estado_civil,telefono,email}, fecha_inclusion
• Snapshot inmutable aunque persona actualice info

PERIODOS_CONTRACTUALES: contrato→FK, numero_periodo(seq), fecha_inicio, fecha_fin, monto_base_uf, monto_final_clp, tipo:'Inicial'|'Renovacion'|'Extension'
• Renovacion auto: 02:01 dia1 sin aviso termino
• Reajustes SIEMPRE sobre valor INICIAL (periodo 1), NO periodo anterior

PAGOS_MENSUALES: contrato→FK, periodo→FK, mes(1-12), anio, monto_esperado_clp(codigo en ultimos 3dig), monto_pagado, fecha_pago, fecha_vencimiento, estado:'Pendiente'|'Pagado'|'Atrasado'|'En Repactacion'|'Pagado Via Repactacion', dias_mora
• Minimo absoluto $1,000 CLP
• Sin pagos parciales auto → admin decide
```
### 3.2 Entidades Financieras
```
CUENTAS_BANCARIAS: banco(enum), numero_cuenta, tipo:'Corriente'|'Vista'|'Ahorro', empresa→FK(multiples), gmail_configurado, LIMITE:999 propiedades
• Validacion async credenciales: "Verificando..."(spinner) | "Activa"(verde) | "Inactiva"(rojo+diagnostico) | "Pausada"(amarillo)

CREDENCIALES_BANCARIAS: cuenta→FK(1:1), usuario_encriptado(AES-256-GCM), clave_encriptada, config_2fa:{tipo,datos}
• Recuperacion: 3 preguntas, requiere 2/3 correctas
• Solo Admin accede
• Reintentos auto fallo banco: 15min → 1h → 4h

AJUSTES_CONTRATO: contrato→FK, tipo:'Descuento'|'Recargo', monto(+), tipo_moneda:'CLP'|'UF', mes_inicio, mes_fin(NULL=indefinido), justificacion(req,min10), creado_por→Admin
• Aplicados ANTES codigo propiedad
• Resultado NUNCA <$1,000
• Multi-moneda: ajuste CLP sobre contrato UF o viceversa (conversion UF dia1 del mes)

HISTORIAL_GARANTIA: contrato→FK, tipo:'Deposito'|'Devolucion'|'Uso Parcial', movimiento_id→FK, monto_clp, fecha, justificacion(req uso parcial)
• Sin intereses ni reajustes → devolucion monto exacto
• Permite operar con garantia parcial (alerta visible)

INGRESO_DESCONOCIDO: monto, fecha_deposito, descripcion_banco, cuenta→FK, sugerencia_ia:{contrato_id,probabilidad,razon}, estado:'Pendiente'|'Asignado'|'Descartado', resuelto_por→Admin, fecha_resolucion
• Solo admin decide, IA sugiere

REPACTACION_DEUDA: arrendatario→FK(no contrato,persiste), deuda_total_original, num_cuotas, monto_cuota, cuotas_pagadas, saldo_pendiente, estado:'Activa'|'Completada'|'Incumplida'
• SIEMPRE del total adeudado
• Recargo auto en futuros cobros
• Pago completo cuota = "a tiempo" para score

CODIGO_DEUDOR(CDD): rango 900-999, arrendatario→FK, contrato_origen→FK, monto_deuda_original
• Independiente nuevos contratos
• Cuota con CDD reemplaza ultimos 3 dig
• IA busca matches exactos
```
### 3.3 Entidades Soporte
```
VALOR_UF: fecha(PK), valor(2dec), fuente:'BC'|'CMF'|'MiIndicador'
• Fallback: BC→CMF→MiIndicador
• Pre-carga dia 27 mes anterior
• Retroactivos: MAXIMO historico del rango

CONFIG_NOTIFICACION: contrato→FK, dias_habilitados:[1,3,5,10,15,20,25](default,100%config), canales_por_dia:{1:['email','whatsapp'],...}, hora_whatsapp(08:00-21:00,default10:00)
• Email SIEMPRE como respaldo
• Config individual por contrato y dia

LOG_COMUNICACION: tipo:'Cobro'|'Aviso'|'Legal'|'Informativo', destinatario_email, destinatario_tel, canal, contenido, timestamp_envio, timestamp_entrega, estado:'Enviado'|'Entregado'|'Fallido'|'Bloqueado', error_code

NOTARIAS: nombre, ciudad, direccion, funcionarios:[{nombre,cargo,email,tel}], emails_contacto[], horarios

CATEGORIA_MOVIMIENTO: nombre(unico), tipo:'Ingreso'|'Gasto', es_sistema:bool
• Protegidas: Arriendo, Garantia Recibida, Servicios Recuperados, Devolucion Garantia, Comision Bancaria, Servicios

FACTURAS_SII: contrato→FK, folio_sii(unico), monto_neto, iva, monto_total, xml_dte, pdf, estado:'Emitida'|'Enviada'|'Aceptada'|'Rechazada', fecha_emision, fecha_envio
• Alerta auto cuando quedan 40 folios
• Dashboard muestra folios disponibles/empresa
```
## 4. REGLAS DE NEGOCIO CRITICAS
### 4.1 Calculo Renta Mensual (Dia1, 02:01 Chile)
```python
def calcular_renta(contrato, mes, anio):
    periodo = obtener_periodo_vigente(contrato, mes, anio)
    valor_uf = obtener_uf(date(anio,mes,1))  # precargado dia27
    if es_retroactivo(contrato,mes,anio): valor_uf = obtener_uf_max_historico(rango)
    monto = periodo.monto_base_uf * valor_uf
    for aj in ajustes_vigentes(contrato,mes):
        monto += (-1 if aj.tipo=='Descuento' else 1) * convertir_clp(aj.monto,aj.moneda)
    if tiene_repactacion(contrato.arrendatario): monto += cuota_repactacion()
    monto = max(int(monto), 1000)  # truncar, minimo absoluto
    return int(str(monto)[:-3] + contrato.propiedad.codigo.zfill(3))  # ej: 523456+042=523042
```
### 4.2 Contratos - Reglas Inmutables
Inicio: dia1 (sin excepciones) | Termino: ultimo dia (auto) | Minimo: $1,000 post-ajustes | Renovacion: auto 02:01 sin aviso | Multi-propiedad: 1 contrato → N propiedades (c/u con codigo) | Max/propiedad: 1 vigente + 1 futuro | Codeudores: 0-3 (snapshot) | Cambio arrendatario: NO → terminar+crear nuevo | Retroactivos: sin limite | ID: inmutable toda la vida | Dia pago: 1-5 (nunca 31)
**Valores sugeridos (100% editables):** Garantia 1 mes | Dia pago 5 | Plazo aviso 60 dias | Pre-alerta admin 30 dias | Duracion 12 meses
**Sistema Tramos (opcional):** Valores diferentes por periodo | Ej: Meses 1-3: $900K, Meses 4-7: 30UF, Meses 8+: 32UF | Al renovar: usa ultimo tramo como base
### 4.3 Notificaciones Inteligentes
Config: dias default [1,3,5,10,15,20,25] 100% personalizable | Canales: Email|WhatsApp|Ambos|Ninguno por dia | Hora WA: 08:00-21:00 (default 10:00) | Email: SIEMPRE respaldo
**Bloqueos WA:** Error 63017 Twilio = bloqueado → marcar arrendatario → notificar admin → solo email | Contador bloqueos rolling 30d | 3+ = "alto riesgo" → advertencia antes reintento | Reset auto 30d sin bloqueos | Sin opt-out (persistentes pero inteligentes)
### 4.4 Sistema Correos Dual
Prioridad: 1)Gmail Empresa → 2)Gmail Cuenta Bancaria → 3)Alerta critica admin | Gmail API OAuth2 exclusivo | Refresh token por cuenta | Templates personalizables
### 4.5 Score de Pago
Formato: "X% (Y de Z meses en sistema)" | X=(Y/Z)*100 redondeado | Ignora meses sin registro (retroactivos) | Con repactacion: pago completo cuota = "a tiempo" | Visible en ficha arrendatario y dashboard
### 4.6 CDD Post-Contrato
Rango 900-999 (100 disponibles) | Contrato termina con deuda → asigna CDD unico → deuda persiste independiente → cuota con CDD en ultimos 3 dig → IA detecta matches | Dashboard separado "Gestion Deudores Post-Contrato" con progreso "Cuota 3/6"
### 4.7 Procesamiento Resiliente
Fallo 1 propiedad → continua con demas → marca fallidas revision manual | Dashboard: "449 exitos/1 fallo" | Admin resuelve individualmente | Fallo Redis → modo degradado sin cache | Email inmediato admin con detalles fallos
### 4.8 Cierre Mes
Auto ultimo dia 23:59:59 | Movimientos posteriores NO afectan mes cerrado | Reapertura: SOLO Admin + justificacion(min20) + AuditLog detallado | Permite asignacion retroactiva
### 4.9 Fecha Pago Real
Vale fecha DETECCION sistema, NO fecha banco | Excepcion falla tecnica: si fallan API+scraping Y fecha banco < actual → usar fecha banco + log "ajustada por falla"
## 5. FLUJOS PRINCIPALES
### 5.1 Terminacion Anticipada (4 Pasos)
**P1-Fecha/Motivo:** fecha efectiva futura + motivo (catalogo+libre)
**P2-Deudas+Ultimo Mes:** ver deudas consolidadas | Opciones: A)Pago completo B)Acuerdo monto menor(sin deuda) C)Abono parcial(diferencia=CDD) D)Sin pago(todo=CDD)
**P3-Docs/Notifs:** carta termino PDF auto + notifs arrendatario + programar devolucion garantia + checklist llaves/inventario
**P4-Confirmacion:** resumen + confirmar | Revertible hasta 5d antes | Post-confirm → estado 'Terminado'
### 5.2 Conciliacion Bancaria Inteligente
Diario auto: API Banco Chile OAuth2(30s timeout) → fallback scraping → fallback manual+alerta
Match exacto (monto+codigo) = asignacion auto | Match parcial = IngresoDesconocido+sugerencia IA | Sin match = IngresoDesconocido
IA: patrones pago, errores digitacion, probabilidad match, pagos combinados, aprende de admin | **IA sugiere, Admin decide, Sistema aprende**
### 5.3 Generacion PDF
Tech: python-docx-template | Proceso: plantilla DOCX → inyectar datos(Jinja2) → DOCX renderizado → PDF → S3/GCS → DocumentoContrato
Plantillas: Contrato arriendo, Carta termino, Aviso cobro, Liquidacion garantia, Anexos modificacion
**Logica representacion:** Arrendador empresa→datos+rep.legal | Arrendador persona→datos socio | Arrendador comunidad→lista socios+rep.designado | Arrendatario empresa→datos+rep.snapshot | Arrendatario persona→datos personales
**Clausulas dinamicas:** Gastos comunes (si/no) | Codeudores (0-3) | Textos segun tipo inmueble | Numeracion auto-ajustada
### 5.4 Firma Mixta con Notaria
**P1:** Admin crea contrato → auto-completa rep.legal → "Generar PDF"
**P2:** "Enviar Aprobacion" → email arrendatario → revisa → aprueba/solicita cambios → notifica admin
**P3:** "Aplicar Firma Electronica" → admin firma electronica avanzada → doc parcialmente firmado
**P4:** Selecciona notaria catalogo → envia doc con firma → tracking estado
**P5:** Arrendatario firma presencial en notaria
**P6 (Manual):** Admin paga notaria → recibe contrato final → sube al sistema → estado 'Vigente'
### 5.5 Marketing Inmobiliario Automatizado
IMPORTANTE: Verificar disponibilidad APIs Yapo/Portal Inmobiliario
Auto: contrato termina → detecta disponibilidad → publica portales (fotos,descripcion,amenidades,precio) → sync consultas | Despublica auto al crear nuevo contrato | Actualiza precios tiempo real | Dashboard consultas unificado
Fallback sin APIs: boton manual + links directos + checklist publicacion
### 5.6 Avisos Retroactivos Post-Renovacion
Escenario: contrato renovado pero admin registra aviso retroactivo
Opciones: A)Revertir renovacion(elimina periodo, solo si no hay pagos) B)Mantener renovacion(aviso para proxima, termino fin periodo actual)
Mostrar impacto antes confirmar | Justificacion obligatoria | Valido si timestamp <= 23:59:59 ultimo dia plazo
### 5.7 Gestion de Notarias
```
NOTARIAS: nombre(req), ciudad(req), direccion, horarios_atencion
FUNCIONARIOS_NOTARIA: notaria→FK, nombre, cargo, email, telefono
```
CRUD completo | Seleccion rapida al enviar contrato | Historial envios por notaria | Dashboard contratos pendientes firma
### 5.8 Dashboard Operacional
**100% personalizable:** columnas arrastrables, filtros guardados, vistas por rol
**Cards KPIs:** Pagos pendientes | Garantias incompletas | Bloqueos WA activos | Contratos por vencer | Deudas criticas
**Modo degradado:** Si falla Redis → HTML estatico con funcionalidad basica
### 5.9 Alertas Administrador
**Dashboard:** Pagos pendientes(badge) | Garantias incompletas(icono) | Bloqueos WA(contador) | Deudas >60d(alerta)
**Email dia 1:** Resumen calculo mensual con exitos/fallos
**WhatsApp inmediato:** Bloqueos detectados con datos contacto
**Pre-alertas:** X dias antes vencimiento plazo aviso termino
**Criticas:** Fallos conciliacion, descuadres saldo, contratos sin garantia
### 5.10 Gestion Documental
```
CONTRATO_DOCUMENTO: contrato→FK, tipo:'Principal'|'Anexo', archivo_url, checksum_sha256, fecha_upload, usuario→FK
GASTO_DOCUMENTO: gasto→FK, archivo_url, checksum_sha256, fecha_upload
INGRESO_DOCUMENTO: ingreso→FK, archivo_url, checksum_sha256, fecha_upload
```
Upload S3/GCS seguro | Validacion tipos(PDF,JPG,PNG) | Max 10MB | Metadata completa | Acceso por permisos
### 5.11 Facturacion Electronica SII
**Automatico dia 1:** Post-calculo renta → genera DTE → firma cert digital → envia API SII → recibe folio
**Solo arrendador=Empresa** | Email separado del aviso cobro | Almacenamiento historial contrato
**Gestion Folios:** Alerta email cuando quedan 40 | Dashboard folios disponibles/empresa | Meta: solicitud auto via API
```
FACTURAS_SII: contrato→FK, folio_sii(unico), monto_neto, iva, monto_total, xml_dte, pdf_url, estado:'Emitida'|'Enviada'|'Aceptada'|'Rechazada', fecha_emision
ALERTA_FOLIO: empresa→FK, folios_restantes, fecha_alerta, notificado:bool
```
### 5.12 Estados PagoMensual Detallados
```
ESTADOS: 'Pendiente' | 'Pagado' | 'Atrasado' | 'En Repactacion' | 'Pagado Via Repactacion' | 'Pagado Acuerdo Termino' | 'Condonado'
```
**Transiciones:** Pendiente→Pagado (conciliacion OK) | Pendiente→Atrasado (vencimiento sin pago) | Atrasado→En Repactacion (plan creado) | En Repactacion→Pagado Via Repactacion (plan completado)
**Auditoria:** Cada cambio estado registra timestamp, usuario, motivo
### 5.13 Criterios Aceptacion Globales
Para TODA funcionalidad: ✅Funciona en TODOS casos | ✅Maneja TODOS errores | ✅Tests >95% cobertura | ✅Docs completa | ✅Performance optima | ✅Seguridad auditada | ✅UX pulida
Si algun criterio NO cumple: ❌NO se acepta | ❌NO avanza siguiente fase | ❌Se corrige hasta PERFECTA
## 6. STACK TECNOLOGICO
| Capa | Tech | | Capa | Tech |
|------|------|---|------|------|
| Backend | Django 5.0 + Django Ninja | | Email | Gmail API OAuth2 |
| BD | PostgreSQL 16 + pgvector | | WhatsApp | Twilio Business |
| Async | Redis + Celery | | IA | LangChain + OpenAI GPT-4 |
| Frontend | React 18 + TS + Vite | | Docs | python-docx-template |
| UI | shadcn/ui + Tailwind | | Storage | AWS S3 / GCS |
| Estado | TanStack Query + Zustand | | Deploy | Docker + GitHub Actions + AWS ECS |
## 7. INTEGRACIONES API
| Servicio | Uso | Auth | Fallback |
|----------|-----|------|----------|
| Banco Chile | Conciliacion | OAuth2 | Scraping autorizado |
| SII Chile | Facturacion | Cert digital | Manual |
| Gmail | Emails | OAuth2 refresh | Alerta admin |
| Twilio | WhatsApp | API Key | Solo email |
| Banco Central | UF | Publica | CMF→MiIndicador→Cache |
| OpenAI | IA | API Key | Reglas basicas |
## 8. REQUISITOS NO FUNCIONALES
**Rendimiento:** Dashboard <2s(cache) | PDF <3s | IA/transaccion <3s | 1000 transacciones <5min | Degradado sin cache <5s
**Cache:** Eventos invalidan: pago_registrado→dashboard,contrato | contrato_modificado→propiedad,empresa | periodo_creado→calculos | Django Signals + Redis keys prefijos + TTL 1h
**Seguridad:** HTTPS TLS 1.3+ | OWASP Top 10 | Credenciales AES-256-GCM | Sesion 30min timeout | Rate limit 100req/min | Captcha 3 intentos | Auditoria completa
**Disponibilidad:** 99.5% uptime | Redis falla→degradado auto | Celery procesa aunque UI falle | Backup incremental diario, completo semanal | RTO 4h, RPO 24h
## 8.1 CONTABILIDAD INTELIGENTE CON IA REGULATORIA
**Motor Contable:** Cada movimiento genera asiento auto | Plan cuentas SII actualizado por IA | Libros digitales tiempo real | Multi-empresa segregada | Trazabilidad completa
**IA Regulatoria (Claude/Gemini):** Detecta diario circulares SII | Identifica beneficios tributarios | Analiza cambios leyes | Sugiere optimizaciones | Actualiza auto formatos/codigos
**F29 Mensual:** Dia10: pre-calculo IVA/PPM/retenciones + sugerencias ahorro | Dia11: dashboard borrador, 1-click aprobar | Dia12: genera XML SII, firma cert, envia API, recibe folio | Dia13: notifica "F29 Presentado Folio:X, Monto:$Y, Vence:Z [Pagar TGR]"
**F22+DDJJ Anual:** Ene-Feb: cierre auto, depreciaciones, RLI, CPT | Mar: analisis 200+ beneficios, simulacion escenarios | Abr: F22 completo + DDJJ 1847,1879,1835 + certs → SII | Notifica "Renta COMPLETA: F22 Folio:X, 8 DDJJ, Ahorro:$Y, Impuesto:$Z"
**Simulador:** "Si facturas hoy vs manana: diferencia $X" | "Activo fijo: ahorro $Y" | Proyeccion F22 | Planificacion flujos
**Dashboard Tributario:** F29 Ene-Pagado | F29 Feb-Por pagar $X | F29 Mar-Borrador $X | Proyeccion Renta | Creditos disponibles | Optimizaciones sugeridas
## 8.2 AGENTE IA CONVERSACIONAL
Arquitectura: Microservicio FastAPI + LangChain/LlamaIndex + API tools controlado
Capacidades: Consultas lenguaje natural 24/7 | "Quien debe +2 meses?" | "Rentabilidad empresa X?" | "Contratos vencen trimestre?" | Analisis complejos instantaneos
Seguridad: Respeta permisos usuario | Solo consultas, no ejecuta | Auditoria interacciones
## 9. ROADMAP
**Fase 1 MVP (3-4m):** CRUDs completos + correos dual Gmail + flujo arrendatarios email→form→aprobacion + contratos con periodos/renovacion + calculo PagoMensual con codigo + notifs Email+WA config + conciliacion API matches exactos + garantias + dashboard degradado
**Fase 2 Inteligencia (2-3m):** IA conciliacion completa + facturacion SII auto + deteccion bloqueos WA + PDFs + score pago + codeudores
**Fase 3 Avanzado (2m):** CDD deudas post-contrato + repactacion auto + portal socios + marketing APIs
**Fase 4 IA Avanzada (2m):** Agente conversacional FastAPI+LangChain + analisis predictivo morosidad + consultas lenguaje natural + dashboard inteligente
**Fase 5 Contabilidad (2-3m):** Motor contable asientos auto + IA regulatoria monitoreo SII + F29 auto mensual + F22+DDJJ auto anual + simulador tributario + dashboard ejecutivo
## 10. LIMITES
| Recurso | Limite | | Recurso | Limite |
|---------|--------|---|---------|--------|
| Propiedades/cuenta | 999 | | Socios sistema | ~15 |
| Codigos propiedad | 001-899 | | Fotos/propiedad | 20 |
| Codigos CDD | 900-999 | | Dias notificacion | 1-31 |
| Codeudores/contrato | 3 | | | |
## 11. VARIABLES ENTORNO
```
DATABASE_URL, SECRET_KEY, ALLOWED_HOSTS, DEBUG, REDIS_URL, CELERY_BROKER_URL
BANCO_CHILE_CLIENT_ID, BANCO_CHILE_CLIENT_SECRET
GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
API_UF_BANCO_CENTRAL, API_UF_CMF, OPENAI_API_KEY
SII_CERT_PATH, SII_CERT_PASSWORD, SII_AMBIENTE
ENCRYPTION_KEY(AES-256,32bytes base64), AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET
TZ=America/Santiago
```
## 12. DECISIONES INMUTABLES
1. CERO tolerancia parches/deuda tecnica
2. Gmail API exclusivo (no SMTP)
3. Sin webscraping principal (solo fallback)
4. Contratos EXTIENDEN con periodos, nunca duplican
5. Formulario web externo registro arrendatarios
6. API SII directa sin intermediarios
7. Notificaciones 100% flexibles contrato/dia/canal
8. Sistema correos dual (empresa o cuenta)
9. Codigo propiedad SIEMPRE ultimos 3 dig monto
10. Snapshot rep.legal inmutable en contrato
11. Score contexto completo "X% (Y de Z)"
12. CDD 900-999 exclusivo deudas post-contrato
13. IA sugiere, humano decide, sistema aprende
14. Fecha pago = deteccion, no fecha banco
15. Procesamiento resiliente: fallos no detienen proceso
16. Cierre mes auto 23:59:59, reapertura solo admin+justificacion
17. Firma mixta: electronica arrendador + presencial notaria
18. Marketing auto: publica/despublica sin intervencion
19. Contabilidad IA: F29/F22 auto, admin solo aprueba
20. Agente IA: consultas lenguaje natural, nunca ejecuta
---
*PRD Maestro LeaseManager v1.0 - 26 versiones consolidadas*

