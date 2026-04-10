# Auditoria Maxima del PRD Maestro - LeaseManager

Fecha de corte: 15/03/2026  
Estado: entregable inicial ejecutable para reescritura del PRD  
Audiencia principal: producto, arquitectura y equipo constructor

## 1. Resumen ejecutivo

El PRD maestro actual es fuerte en continuidad de negocio, trazabilidad y endurecimiento frente a versiones anteriores, pero sigue mezclando cuatro niveles que conviene separar antes de construir: regla de dominio, decision arquitectonica, gate externo y aspiracion de roadmap.

La conclusion principal de esta auditoria es que el problema del documento no es que "todo este mal"; el problema es que congelo demasiado pronto varias decisiones que todavia deberian ser hipotesis, especialmente en banco, SII, stack, identidad de emision y alcance de automatizacion.

Hallazgos principales:

- El conflicto mas grave del modelo es la colision entre codigos de propiedad `001-999` y codigo de deudor post-contrato `900-999`; hoy el PRD declara ambos como compatibles, pero se pisan.
- La estrategia bancaria no deberia ser "producto = Banco de Chile"; deberia ser "producto = interfaz bancaria + primer provider Banco de Chile".
- `Gmail por cuenta bancaria` no es una abstraccion sana del dominio; la identidad de envio debe anclarse a una entidad legal u operativa, no a una cuenta bancaria.
- `API SII` esta tratada como una sola cosa, cuando en la practica hay que separar DTE, boleta, consultas, certificados, folios y obligaciones tributarias de mayor sensibilidad.
- El stack base va en la direccion correcta en su nucleo, pero el PRD congela demasiadas decisiones de implementacion. `pgvector`, `Zustand`, `shadcn/ui`, `Tailwind` y `python-docx-template` no deberian ser norma de producto.
- El documento tiene buena gobernanza declarativa, pero la incumple al llamar "cerradas" o "congeladas" decisiones que esta auditoria reabre por falta de evidencia externa suficiente.
- Seguridad, privacidad, retention y cumplimiento chileno estan subespecificados para el nivel de automatizacion prometido.

Cobertura revisada del maestro:

- 21 secciones `##`
- 399 parrafos aproximados
- 1150 lineas
- pasada estructural, de dominio, tecnica y microeditorial sobre el maestro completo

## 2. Corpus congelado

| Fuente | Rol en la auditoria |
|---|---|
| `PRD_MAESTRO_DEFINITIVO.md` | documento auditado principal |
| `AUDITORIA_PRDS_1_26.md` | trazabilidad historica por version |
| `MATRIZ_CONSOLIDACION_TEMATICA.md` | trazabilidad por tema |
| `PRD_UNIFICADO.md` | baseline previo con sobrepromesas y contradicciones utiles para contraste |
| `prd.txt` | metodologia de unificacion |
| `CLAUDE.md` | resumen operativo del proyecto y sus reglas maestras |
| `analizar/prd1.txt` a `analizar/prd26.txt` | fuente historica consolidada |

## 3. Taxonomia operativa usada

### 3.1 Gates de seccion

| Gate | Significado |
|---|---|
| `Rojo` | no debe pasar intacta al nuevo PRD; contiene contradiccion material, freeze prematuro o gap estructural |
| `Amarillo` | la seccion es rescatable, pero requiere poda, aclaracion o mover contenido a otro artefacto |
| `Verde` | la seccion puede sobrevivir con ajustes menores |

### 3.2 Decisiones de auditoria

| Estado | Significado |
|---|---|
| `Mantener` | conservar la regla casi intacta |
| `Reescribir` | preservar la intencion, cambiar la formulacion o el mecanismo |
| `Eliminar` | sacar del PRD canonico |
| `Dividir` | separar en dos o mas artefactos o reglas |
| `Mover` | sacar del PRD canonico hacia ADR, politica, anexo o backlog |
| `Validar externamente` | no congelar hasta cerrar evidencia oficial |

## 4. Section gates del maestro

| Seccion | Rango | Tipo dominante | Gate | Decision |
|---|---:|---|---|---|
| `1. Estatus del documento` | 3-19 | gobernanza documental | `Amarillo` | mantener, corrigiendo links y tono de "fuente unica" |
| `2. Metodologia de consolidacion` | 20-88 | metodologia historica | `Rojo` | dividir: dejar historia, reabrir decisiones cerradas |
| `3. Vision del producto` | 89-102 | vision | `Amarillo` | reescribir para separar mision de ambicion |
| `4. Principios rectores` | 103-195 | principios y gobernanza | `Amarillo` | mantener la precedencia; mover cultura de ingenieria fuera del PRD normativo |
| `5. Localizacion, usuarios y KPIs` | 196-236 | producto y medicion | `Amarillo` | reescribir roles finos y KPIs medibles |
| `6. Alcance funcional` | 237-253 | scope | `Amarillo` | mantener, con fases y gates mas estrictos |
| `7. Modelo de dominio` | 254-699 | dominio canonico | `Rojo` | reescribir por bounded contexts y corregir colisiones |
| `8. Reglas de negocio` | 700-955 | reglas canonicas | `Rojo` | reescribir, distinguiendo invariantes duros de politicas configurables |
| `9. Flujos operacionales` | 956-1019 | workflows | `Amarillo` | mantener happy paths, agregar excepciones y SLA |
| `10. Integraciones y gates` | 1020-1258 | dependencias externas | `Rojo` | dividir por provider y redefinir readiness |
| `11. Seguridad, resiliencia y auditoria` | 1259-1306 | NFR y compliance | `Rojo` | reescribir con controles concretos |
| `12. Requisitos tecnicos y UX` | 1307-1345 | arquitectura y UX | `Rojo` | mover decisiones tecnicas a ADR; mantener UX/NFR |
| `13. Roadmap maestro` | 1346-1386 | roadmap | `Rojo` | reordenar por validacion y riesgo regulatorio |
| `14. Fuera de alcance` | 1387-1397 | boundaries | `Amarillo` | mantener, ajustando segun estrategia bancaria y de portales |
| `15. Criterios de aceptacion` | 1398-1438 | QA y acceptance | `Rojo` | reescribir como matriz ejecutable de pruebas |
| `16. Formulas y limites` | 1439-1463 | apendice normativo | `Amarillo` | mantener formula; corregir namespace de codigos |
| `17. Configuracion externa` | 1464-1479 | insumos tecnicos | `Amarillo` | mover parte a ADR/ops manual |
| `18. Trazabilidad por version` | 1480-1510 | historia | `Verde` | mantener como anexo historico |
| `19. Documentos de apoyo` | 1511-1518 | referencia | `Verde` | mantener |
| `20. Matriz resumida de decisiones` | 1519-1534 | resumen canonicidad | `Amarillo` | rehacer luego de reabrir decisiones |
| `21. Glosario minimo` | 1535-1548 | terminologia | `Amarillo` | ampliar y normalizar |

## 5. Hallazgos bloqueantes

### H-001

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `7.5` lineas `376-378`, `7.17` lineas `675-677`, `16.2` lineas `1457-1459`
- Categoria: modelo de dominio / conciliacion
- Severidad: bloqueante
- Hallazgo: el PRD define `codigo_propiedad` en rango `001-999` por cuenta y define `Codigo de deudor post-contrato` en rango `900-999`. Ambos namespaces se superponen.
- Impacto: la conciliacion exacta deja de ser deterministica y el limite real de propiedades por cuenta deja de ser `999`.
- Recomendacion: reservar namespaces disjuntos o eliminar el mecanismo `900-999` y modelar deuda residual con referencia explicita distinta al codigo de propiedad.
- Estado: `Reescribir`

### H-002

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `2.4`, `8.8`, `10.1`, `20`
- Categoria: estrategia de producto / integraciones
- Severidad: bloqueante
- Hallazgo: el PRD trata a Banco de Chile como regla de producto, no como primer provider de una interfaz bancaria.
- Impacto: el producto queda comercialmente acoplado a un banco, reduce escalabilidad y obliga a reescribir dominio si luego entra otro provider.
- Evidencia externa: Banco de Chile si ofrece productos API para empresas, incluyendo cartola y movimientos, pero eso valida el provider, no la decision de cerrar el producto a un solo banco.
- Recomendacion: convertir banco en capacidad pluggable. `Banco de Chile` debe quedar como primer adapter oficial, no como limite canonico del producto.
- Estado: `Dividir`

### H-003

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `10.3` lineas `1093-1119`
- Categoria: dominio / comunicaciones / identidad operativa
- Severidad: bloqueante
- Hallazgo: la regla `Gmail por empresa o por cuenta bancaria` mezcla identidad de emision con una cuenta recaudadora.
- Impacto: dificulta cumplimiento, ownership de OAuth, delegacion, revocacion, auditoria y experiencia del arrendatario.
- Evidencia externa: Gmail API opera sobre OAuth y cuenta emisora; el concepto tecnico natural es usuario o identidad administrada, no cuenta bancaria.
- Recomendacion: reemplazar por un modelo `IdentidadDeEnvio` ligado a empresa, administrador operativo o marca autorizada; la cuenta bancaria solo puede ser metadata contextual.
- Estado: `Reescribir`

### H-004

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `10.5`, `13.5`, `15.3`
- Categoria: tributacion / cumplimiento / integraciones
- Severidad: bloqueante
- Hallazgo: `API SII` esta modelada como una sola integracion y el roadmap mezcla DTE, borradores, presentaciones tributarias y automatizacion avanzada bajo la misma etiqueta.
- Impacto: se sobrepromete automatizacion sin descomponer readiness por flujo, certificado, folios, tipo de documento, aprobacion humana y validacion legal.
- Evidencia externa: SII mantiene servicios y flujos separados para facturacion electronica y boleta electronica; el PRD necesita granularidad por capability, no un bloque unico.
- Recomendacion: separar como minimo `DTE emision`, `consulta/estado`, `boleta`, `libros/archivos`, `presentaciones tributarias asistidas` y `presentaciones tributarias automatizadas`.
- Estado: `Dividir`

### H-005

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `12.1` y `12.4`
- Categoria: arquitectura / gobernanza
- Severidad: bloqueante
- Hallazgo: el PRD congela decisiones de implementacion que deberian vivir en ADR o arquitectura de referencia.
- Impacto: si el equipo descubre una mejor opcion, el cambio parece "romper el producto" cuando solo deberia ajustar la implementacion.
- Recomendacion: mover `Django Ninja`, `Celery`, `Zustand`, `shadcn/ui`, `Tailwind CSS`, `python-docx-template` y `pgvector` fuera del PRD normativo. El PRD debe fijar capacidades, no librerias.
- Estado: `Mover`

### H-006

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `7.2-7.5`, `7.9`, `10.3`, `10.5`
- Categoria: dominio / modelo legal-operativo
- Severidad: bloqueante
- Hallazgo: falta una entidad explicita para separar propietario, administrador operativo, emisor tributario y titular de cuenta bancaria.
- Impacto: varias reglas parecen correctas por separado, pero no hay una forma limpia de saber quien recauda, quien factura, quien firma y quien comunica.
- Recomendacion: introducir un bounded context de operacion con entidades del tipo `MandatoOperacion`, `IdentidadDeEnvio`, `EntidadFacturadora` o equivalentes.
- Estado: `Reescribir`

### H-007

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `8.2`
- Categoria: reglas de negocio / politica configurable
- Severidad: bloqueante
- Hallazgo: `inicio dia 1`, `termino ultimo dia` y `dia_pago_mensual entre 1 y 5` estan formulados como invariantes universales del dominio, pero el documento no los justifica como ley ni como segmentacion de producto.
- Impacto: el PRD puede excluir casos reales del mercado o forzar excepciones futuras no modeladas.
- Recomendacion: si la decision es de producto, declararla como `policy` de LeaseManager v1 y no como verdad universal del dominio; si es legal, anexar fundamento normativo.
- Estado: `Validar externamente`

### H-008

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `2.4`, `12.4`, `20`
- Categoria: gobernanza documental
- Severidad: bloqueante
- Hallazgo: el documento declara decisiones "cerradas" y "congeladas" dentro del mismo artefacto que pretende ser auditado y evolucionable.
- Impacto: sesga la lectura, dificulta governance y vuelve el PRD autorreferente.
- Recomendacion: separar `PRD canonico`, `ADR`, `gates externos` y `anexo historico`. Ningun artefacto deberia blindarse a si mismo.
- Estado: `Dividir`

## 6. Hallazgos mayores

### H-009

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `5.4`
- Categoria: KPIs
- Severidad: mayor
- Hallazgo: los KPIs no definen baseline, owner, fuente de medicion ni ventana de calculo.
- Recomendacion: convertir cada KPI en metrica operable con formula, baseline, periodicidad y responsable.
- Estado: `Reescribir`

### H-010

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `11`
- Categoria: seguridad / compliance
- Severidad: mayor
- Hallazgo: seguridad esta expresada como principios generales, pero faltan rotacion de secretos, KMS, clasificacion de datos, retencion, borrado, auditabilidad inmutable y segregacion por tenant/empresa.
- Evidencia externa: Chile promulgo la Ley `21.719` sobre proteccion de datos personales; el PRD no refleja todavia un programa minimo de cumplimiento.
- Recomendacion: agregar un capitulo de `Data Protection & Security Controls` con politicas concretas.
- Estado: `Reescribir`

### H-011

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `4.4`, `10.7`, `13.4`
- Categoria: IA / gobierno de datos
- Severidad: mayor
- Hallazgo: la IA esta bien limitada en decisiones criticas, pero faltan reglas de redaccion, masking, retention, provider routing, trazabilidad de prompts y uso permitido por clase de dato.
- Recomendacion: mover limites operativos de IA a un ADR y agregar politica de datos sensibles.
- Estado: `Dividir`

### H-012

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `10.6`, `13.3`
- Categoria: integraciones inmobiliarias
- Severidad: mayor
- Hallazgo: Portal Inmobiliario muestra evidencia de integraciones API, pero Yapo no presenta una documentacion publica equivalente encontrada en la busqueda oficial realizada el `15/03/2026`.
- Impacto: no conviene prometer ambos canales con el mismo peso.
- Recomendacion: dejar `Portal Inmobiliario` como `validar externamente` y `Yapo` como `no canonico hasta partnership o API publica verificable`.
- Estado: `Validar externamente`

### H-013

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `12.1`, `13.4`
- Categoria: arquitectura / IA
- Severidad: mayor
- Hallazgo: `pgvector` aparece en stack base aunque las funciones semanticas fuertes viven en fases posteriores.
- Recomendacion: sacar `pgvector` del stack obligatorio de fase 1 y activarlo por gate cuando exista un caso real de busqueda semantica o retrieval.
- Estado: `Mover`

### H-014

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `9.3`, `12.1`
- Categoria: documentos
- Severidad: mayor
- Hallazgo: el flujo documental esta mejor especificado que la tecnologia documental. El PRD fija `python-docx-template`, pero no define criterio de fidelidad, versionado de plantillas, firmas, conversion a PDF ni soporte de variaciones notariales.
- Recomendacion: convertir la generacion documental en ADR con evaluacion comparativa entre `DOCX-first` y `HTML/CSS -> PDF`.
- Estado: `Mover`

### H-015

- Fuente: `PRD_MAESTRO_DEFINITIVO.md`
- Ubicacion exacta: `15`
- Categoria: QA / acceptance
- Severidad: mayor
- Hallazgo: los escenarios de aceptacion son utiles como humo inicial, pero no son suficientes para una plataforma financiera-documental con integraciones.
- Recomendacion: reescribir como matriz de pruebas por contexto: happy path, excepciones, degradado, seguridad, permisos, backfill, retroactividad, auditoria y rollback.
- Estado: `Reescribir`

## 7. Decision records reabiertos

| Tema | Decision actual | Veredicto | Opcion recomendada | Consecuencia |
|---|---|---|---|---|
| Estrategia bancaria | solo Banco de Chile API oficial | reabrir | interfaz bancaria + provider inicial Banco de Chile | protege escalabilidad y evita lock-in de dominio |
| Identidad de envio | Gmail por empresa o cuenta bancaria | reabrir | `IdentidadDeEnvio` separada del banco | ordena OAuth, ownership y auditoria |
| SII | una sola `API SII` por fases | reabrir | capabilities separadas por flujo tributario | reduce sobrepromesa y mejora readiness |
| API backend | `Django Ninja` congelado | reabrir | PRD no fija framework; ADR decide entre DRF/Ninja por modulo | evita mezclar producto con implementacion |
| Async | `Redis + Celery` congelado | reabrir parcialmente | Celery v1 recomendado; reevaluar motor durable solo si aparecen workflows de larga vida | baja complejidad inicial |
| Vector search | `pgvector` en stack base | reabrir | gate a fase 4 | elimina complejidad sin caso activo |
| Frontend state/UI | `Zustand`, `shadcn/ui`, `Tailwind` canonicos | reabrir | dejarlos como stack sugerido, no normativo | libertad tecnica sin romper producto |
| Portales | Yapo + Portal en roadmap | reabrir | Portal validar; Yapo no canonico hasta evidencia | evita roadmap ficticio |
| Contratos dia 1/ultimo dia | invariante duro | reabrir parcialmente | policy de producto v1 o regla normada con fundamento | mejor trazabilidad de excepciones |
| Politica "sin soluciones temporales" | norma central del PRD | mover | mantener como principio de ingenieria, no como regla normativa de dominio | limpia el documento |

## 8. Matriz de stack recomendada

| Area | Estado actual del PRD | Evaluacion de auditoria | Recomendacion |
|---|---|---|---|
| Arquitectura base | monolito implicito con stack fijo | correcta direccion, freeze excesivo | `Mantener` monolito modular como arquitectura de referencia |
| Backend core | `Django 5` | muy buen fit para ERP con auth, admin, ORM y backoffice | `Mantener` |
| Capa API | `Django Ninja` fijo | viable, pero no deberia ser verdad de producto | `Mover` a ADR; sesgo inicial a `DRF` para API core y `Ninja` opcional en endpoints especializados |
| Base de datos | `PostgreSQL 16` | excelente fit transaccional | `Mantener` |
| Vector search | `pgvector` obligatorio | prematuro para fase 1 | `Mover` a gate de IA/semantica |
| Jobs y colas | `Redis + Celery` fijo | fit razonable para notificaciones, sincronizaciones y pipelines operativos | `Mantener` para v1 |
| Workflow durable | no modelado | puede aparecer por SII, firma, notaria o integraciones complejas | `Descartar por ahora`, reabrir solo si nacen workflows de larga vida |
| Frontend | `React 18 + TypeScript + Vite` | stack saludable para SPA/backoffice | `Mantener` |
| Estado cliente | `TanStack Query + Zustand` fijo | Query si; Zustand depende del diseno final | `Mantener Query`, `Mover Zustand` a ADR |
| UI | `shadcn/ui + Tailwind CSS` fijo | decision de implementacion, no de producto | `Mover` a ADR |
| Documentos | `python-docx-template` fijo | requiere comparativa legal/operativa | `Mover` a ADR documental |
| Email | `Gmail API` directo | viable como provider inicial | `Mantener` como adapter, no como unica identidad de emision |
| Mensajeria | `Twilio WhatsApp Business` | viable con templates, opt-in y ventanas de conversacion | `Mantener` como provider inicial |
| Observabilidad | no definida como stack | gap | `Agregar` capacidad obligatoria de logging, tracing y alerting |
| Secretos | solo regla general de cifrado | gap | `Agregar` secret manager/KMS y rotacion como requisito tecnico obligatorio |

Stack recomendado para arrancar bien:

1. Monolito modular en `Django 5 + PostgreSQL`.
2. Frontend `React + TypeScript + Vite`.
3. `Celery + Redis` para tareas operativas y sincronizaciones.
4. Capa API decidida por ADR, no por PRD.
5. `pgvector` fuera del MVP obligatorio.
6. Librerias de UI y estado como decisiones de implementacion, no de producto.

## 9. Pasada microeditorial

Hallazgos de redaccion, forma y semantica:

- Los links locales del corpus usan `D:/...` en vez de `/D:/...`, por lo que quedan peor alineados con el entorno Codex Desktop.
- El documento mezcla lenguaje normativo y lenguaje de cierre historico: `definitivo`, `cerrado`, `congelado`, `canonico`, `no opcional`. Eso contamina la auditabilidad.
- Conviven entidades en espanol natural con nombres de clase o tabla (`HistorialGarantia`, `PagoMensual`, `ContratoPropiedad`) sin una convencion explicita.
- Los estados y reglas combinan lenguaje humano y semitecnico sin separar bien enum, politica y explicacion.
- Hay terminos cercanos pero no equivalentes que deberian unificarse en glosario: `operacion manual`, `resolucion manual`, `contingencia manual`, `fallback permitido`, `modo degradado`, `readiness`.
- Los KPIs usan formatos heterogeneos (`99,5%`, `<2 segundos`, `>95%`) sin convencion de parseo ni criterio de medicion.
- El PRD usa buen detalle en algunos bloques, pero otros quedan en sustantivos generales: `motor contable integrado`, `analitica predictiva`, `evolucion contable`, `integracion directa`.

Decision editorial:

- `Mantener` la prosa sobria y estructurada.
- `Reescribir` todo el lenguaje de blindaje autorreferente.
- `Ampliar` glosario y convenciones de nombres.
- `Separar` regla normativa, ejemplo, flujo y anexo tecnico.

## 10. Plan maestro de reescritura

### 10.1 Nuevo set de artefactos

1. `PRD_CANONICO.md`: solo objetivo, dominio, reglas, flows, acceptance y gates.
2. `ADR_ARQUITECTURA_001.md` en adelante: decisiones de stack, API, documentos, async, observabilidad, secretos.
3. `MATRIZ_GATES_EXTERNOS.md`: banco, SII, WhatsApp, email, portales, IA.
4. `BACKLOG_INVESTIGACION.md`: temas no congelables todavia.
5. `ANEXO_HISTORICO_PRDS.md`: trazabilidad de `prd1` a `prd26`.

### 10.2 Orden recomendado de reescritura

1. Reescribir vision, alcance y governance del documento.
2. Rehacer el modelo operativo: propietario, administrador, facturador, emisor y cuenta recaudadora.
3. Corregir namespace de codigos y modelo de deuda residual.
4. Reescribir reglas contractuales, distinguiendo invariantes de politicas v1.
5. Separar integraciones por provider y por capability.
6. Sacar stack fijo del PRD y moverlo a ADR.
7. Rehacer acceptance y matriz de pruebas.
8. Volver a emitir la matriz resumida canonicamente despues de cerrar ADR y gates.

### 10.3 ADR obligatorios

- ADR-001: estrategia bancaria multi-provider
- ADR-002: identidad de envio y ownership de canales
- ADR-003: descomposicion funcional de SII
- ADR-004: framework de API para backoffice y APIs externas
- ADR-005: estrategia documental y conversion a PDF
- ADR-006: seguridad de secretos, claves y auditoria inmutable
- ADR-007: activacion de IA semantica y `pgvector`

### 10.4 Backlog de investigacion faltante

- validar si `dia_pago_mensual 1-5` es regla de negocio real del target o simplificacion historica
- validar legalmente firma, notaria y retencion documental por tipo de contrato
- definir retention y borrado bajo normativa chilena de datos personales
- validar evidencia publica o partnership para Yapo
- validar si el primer release requiere portal de socios o solo reporting filtrado

## 11. Fuentes externas primarias usadas

Integraciones y regulacion:

- Banco de Chile Developers: [API Portal de Empresas](https://developers.bancochile.cl/) y [producto Cartola y Movimientos](https://developers.bancochile.cl/producto/cartola-y-movimientos)
- Google: [Gmail API Overview](https://developers.google.com/workspace/gmail/api/guides)
- Google: [Create and send mail](https://developers.google.com/gmail/api/guides/sending)
- Twilio: [WhatsApp Best Practices and FAQs](https://www.twilio.com/docs/whatsapp/best-practices-and-faqs)
- SII: [Servicios de Factura Electronica](https://www.sii.cl/servicios_online/1039-.html)
- SII: [Boleta Electronica](https://www.sii.cl/servicios_online/1036-.html)
- CMF: [API CMF Chile](https://api.cmfchile.cl/)
- MiIndicador: [API publica](https://mindicador.cl/api)
- BCN: [Ley 21.719 sobre proteccion y tratamiento de datos personales](https://www.bcn.cl/leychile/navegar?idNorma=1219501)

Stack y arquitectura:

- Django: [Meet Django](https://www.djangoproject.com/start/overview/)
- Django REST Framework: [Tutorial / serialization and auth](https://www.django-rest-framework.org/tutorial/1-serialization/)
- Django Ninja: [Official documentation](https://django-ninja.dev/)
- Celery: [First steps](https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html)
- pgvector: [Official project](https://github.com/pgvector/pgvector)
- Portal Inmobiliario: [Integracion via API / CRM publicada en canal oficial](https://www.portalinmobiliario.com/blog/herramientas-principiantes/integracion-crm-portalinmobiliario-como-publicar-tus-propiedades-via-api/)

Nota sobre Yapo:

- Se realizo busqueda dirigida sobre dominio oficial el `15/03/2026` y no se encontro evidencia publica equivalente a un developer program estable. Esta conclusion es una inferencia por ausencia de fuente oficial visible y debe tomarse como `insuficiencia de evidencia`, no como negacion absoluta de capacidades privadas.

## 12. Conclusiones ejecutables

- La funcion de negocio del producto se preserva.
- El PRD actual no debe pasarse a construccion como si ya fuera canonico e inatacable.
- El nuevo PRD debe salir de una separacion limpia entre dominio, ADR, gates y anexos historicos.
- El stack base recomendado sigue siendo monolito modular en Django/PostgreSQL con frontend React, pero sin congelar librerias accesorias desde el PRD.
- Las mayores reaperturas obligatorias son: banco multi-provider, namespace de codigos, identidad de envio, descomposicion SII y control de seguridad/compliance.

