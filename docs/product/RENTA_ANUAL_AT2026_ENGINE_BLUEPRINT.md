# Blueprint motor Renta Anual AT2026

Estado: diseno propio derivado de evidencia funcional EDIG/SII, no normativa.

Este documento traduce la investigacion local de EDIG AT2026 a una arquitectura
implementable para LeaseManager. No copia codigo, formulas, filas MDB ni modelo
propietario. Usa solo senales estaticas, metadata de esquema y fuentes SII para
definir que piezas propias debe tener un motor anual tributario revisable.

## Evidencia base

La evidencia local disponible esta en artefactos versionados y salidas
ignoradas bajo `local-evidence/`:

- `RENTA_ANUAL_EDIG_AT2026_MAPPING.md`: matriz EDIG -> LeaseManager.
- `analyze-edig-at2026.ps1`: inventario estatico de archivos, ejecutables,
  plantillas, reportes, tokens estructurales y senales funcionales.
- `extract-edig-mdb-schema.ps1`: metadata de tablas/columnas desde copias
  temporales de MDB nucleo, sin leer filas.

La corrida local de esquema extrajo 7/7 MDB nucleo, con 205 tablas y 5.494
columnas. La distribucion funcional observada fue:

| Capa observada | Evidencia estatica | Lectura para LeaseManager |
| --- | --- | --- |
| Maestros/capacidades | `comun.MDB`, `CANova.mdb` | empresa, contribuyente, usuario, productos/capacidades y estado de modulos son prerequisito anual |
| F29/PPM mensual | `F29LGH.MDB`, `IVASTD26.EXE`, plantillas F29 | obligaciones mensuales alimentan creditos, PPM, IVA y consistencia anual |
| Parametria regimen | `R14PARA26.MDB`, tablas por codigos DJ/F22, items RLI/CPT | reglas tributarias deben versionarse por ano tributario/regimen |
| Registros 14 | `Reg14.MDB`, senales RLI/CPT/RAI/SAC/retiros/dividendos | antes del F22 existe una capa de registros empresariales |
| PRO/F22 | `PRO26.MDB`, `GNPRO26.EXE`, plantillas `#fld####` | F22 es artefacto de salida/preview/export, no fuente primaria |
| Bienes raices/arriendos | senales en `PRO26.MDB` y parametria | propiedades, arriendos y contribuciones deben normalizarse como subdominio anual |
| Reportes/respaldo | reportes RLI/CPT/RAI/SAC/Control | el motor debe producir dossier revisable, no solo payload tecnico |
| Upload/export | plantillas/importadores, DLLs y carpeta de salida | presentacion final queda bajo gate externo y formato/certificacion vigente |

## Decision de arquitectura

LeaseManager no debe hacer `ledger -> F22` directo. Debe hacer:

```text
cierres mensuales + F29/PPM + ledger + patrimonio + contratos + socios
    -> paquete fuente anual
    -> normalizador tributario AT
    -> RLI/CPT/RAI/SAC/DDJJ/respaldos
    -> preview F22 y export controlado
    -> revision responsable y gate SII
```

La IA puede asistir revision y explicacion, pero el core no debe decidir ni
presentar renta final de forma autonoma.

## Matriz de decision para integracion SII

Antes de automatizar cualquier salida hacia SII, LeaseManager debe clasificar
la capacidad con evidencia oficial vigente. La existencia de un formulario o de
una certificacion tecnica no prueba que el criterio tributario pueda quedar
automatizado.

| Capacidad | Tratamiento v1 | Evidencia requerida | Decision |
| --- | --- | --- | --- |
| DTE/boleta/factura | integracion tecnica posible | ambiente de certificacion, formato XML, firma, CAF, web service o instructivo vigente | implementar solo con gate DTE, certificado/caf seguro y rollback |
| Consulta/estado DTE | integracion tecnica posible | web service vigente y autenticacion compatible | automatizar consulta, no decisiones tributarias |
| F29 mensual | preparacion y revision supervisada | formato/medio vigente, responsable, evidencia mensual y fuente oficial/experta | preparar borrador/paquete; presentacion queda bajo gate |
| DDJJ anual | paquete revisable | formulario vigente, medio SII, responsable y reglas por AT | generar dossier/export controlado; no presentar sin autorizacion |
| F22/renta anual | preview y dossier, no decision final autonoma | reglas AT aprobadas, fuente oficial/experta, formato/certificacion vigente y revision responsable | bloquear cierre/presentacion final hasta aprobacion |
| Automatizacion por navegador | ultimo recurso operativo | runbook, usuario responsable, datos controlados y captura de evidencia | solo asistida, supervisada y reversible; no reemplaza API |

Si no existe API oficial o medio tecnico estable para una capacidad, el sistema
debe producir archivos, reportes, hashes y pasos de revision. No debe simular
certeza fiscal mediante navegacion automatica ni por inferencia de IA.

## Componentes propios

| Componente | Responsabilidad | Entrada | Salida | Gate |
| --- | --- | --- | --- | --- |
| `AnnualTaxSourceBundle` | Congelar fuentes anuales no sensibles | cierres, ledger, F29/PPM, contratos, propiedades, socios, certificados | snapshot anual trazable | 12 cierres aprobados y refs no sensibles |
| `TaxYearRuleSet` | Versionar reglas por AT/regimen | fuente oficial/experta, hashes, vigencia | reglas aprobadas/condicionadas | no se activa sin fuente aprobada |
| `AnnualTaxProfile` | Fijar empresa/regimen/responsable | empresa, configuracion fiscal, representante | perfil anual | configuracion fiscal activa |
| `MonthlyTaxFact` | Normalizar hechos mensuales | F29, cierre mensual, liquidaciones, pagos | base mensual anualizable con hash | cierre aprobado y refs no sensibles |
| `AnnualTaxNormalizer` | Transformar fuentes a registros intermedios | source bundle + rule set | RLI, CPT, RAI, SAC, DDJJ base | no calcula sin rule set vigente |
| `AnnualTaxWorkbook` RLI | Determinar lineas RLI trazadas | `TaxCodeMapping` + `MonthlyTaxFact` | lineas RLI, hashes, warnings | origen y fuente por linea |
| `AnnualTaxWorkbook` CPT | Determinar capital propio tributario preparatorio | `TaxCodeMapping` + `MonthlyTaxFact` | lineas CPT, hashes y warnings | no cerrar con warnings |
| `AnnualEnterpriseRegisterSet` | Construir RAI/SAC/retiros/dividendos | RLI/CPT/socios/movimientos | registros empresariales | saldos iniciales y movimientos trazados |
| `AnnualRealEstateSection` / `AnnualRealEstateItem` | Normalizar bienes raices/arriendos | propiedades, contratos, pagos, distribuciones y contribuciones | seccion anual, items por propiedad y respaldo | fuente SII/experta para codigos y contribuciones |
| `AnnualTaxArtifactMatrix` / `AnnualTaxArtifactMatrixItem` | Conectar fuentes anuales con DDJJ/F22 revisables | source bundle, rule set, config fiscal, resumen anual, RLI/CPT, registros y bienes raices | matriz por destino, medio, fuente, responsable, warnings y hash | items DDJJ/F22 activos y sin warnings pendientes |
| `DdjjPackageBuilder` | Preparar DDJJ/certificados | matriz DDJJ, registros, socios, certificados | paquetes DDJJ revisables | medio SII vigente por formulario |
| `F22DraftBuilder` | Mapear a codigos F22 | matriz F22, registros intermedios y DDJJ | preview F22 | formato/certificacion vigente |
| `AnnualTaxDossier` | Generar respaldo revisable | todo lo anterior | PDF/HTML/resumen hash | responsable de revision |
| `AnnualTaxExport` | Emitir archivo controlado | F22/DDJJ aprobados | export no sensible | autorizacion explicita y gate SII |

## Contratos de datos minimos

Los modelos exactos pueden cambiar, pero el motor debe preservar estos
contratos:

| Contrato | Campos minimos | Razon |
| --- | --- | --- |
| Fuente anual | `anio_tributario`, `anio_comercial`, `empresa`, `source_kind`, `source_label`, `authorization_ref`, `hash_fuentes` | probar origen y alcance |
| Regla AT | `anio_tributario`, `regimen`, `version`, `fuente_ref`, `estado`, `hash_normativo` | evitar reglas implicitas |
| Linea normalizada | `codigo_interno`, `origen`, `monto`, `signo`, `formula_ref`, `evidencia_ref`, `warnings` | trazabilidad de cada monto |
| Registro empresarial | `tipo_registro`, `saldo_inicial`, `movimientos`, `saldo_final`, `fuente_saldo` | RAI/SAC no puede inventar saldos |
| Paquete DDJJ | `formulario`, `medio_sii`, `periodo`, `registros`, `responsable_revision_ref`, `paquete_ref` | DDJJ revisable antes de F22 |
| Draft F22 | `codigo_f22`, `valor`, `fuente_linea`, `estado_revision`, `borrador_ref` | F22 como salida explicable |
| Decision responsable | `responsable_ref`, `accion`, `observacion`, `evidencia_ref`, `timestamp` | boundary humano/experto |

## Orden de implementacion recomendado

1. `stage6-tax-year-ruleset`: tablas propias de `TaxYearRuleSet` y
   `TaxCodeMapping`, sin formulas finales. Implementado como primera capa
   tecnica: modelos, migracion, API/snapshot/admin, bootstrap demo, guard de
   generacion anual y readiness bloqueante si falta regla aprobada o mapping
   trazable.
2. `stage6-source-bundle`: congelar fuentes anuales desde cierres/F29/ledger
   controlados. Implementado como `AnnualTaxSourceBundle`: modelo, migracion,
   API/snapshot/admin redactados, hash de payload normalizado, enlace a
   `ProcesoRentaAnual` y readiness bloqueante si falta bundle congelado o si
   su metadata queda desalineada.
3. `stage6-monthly-tax-facts`: crear hechos mensuales anualizables desde F29,
   pagos, liquidaciones y cierres. Implementado como `MonthlyTaxFact`: una
   fila por empresa/ano/mes con cierre aprobado, F29 opcional, liquidacion
   opcional, resumen mensual no sensible, `hash_hecho`, API/snapshot/admin
   redactados y readiness bloqueante si un proceso anual trazable no conserva
   los doce meses normalizados en su resumen.
4. `stage6-rli-cpt-skeleton`: estructura RLI/CPT con lineas trazadas y
   warnings, sin afirmar calculo fiscal final. Implementado como
   `AnnualTaxWorkbook` y `AnnualTaxWorkbookLine`: genera workbooks RLI y CPT
   desde `TaxCodeMapping` activo y `MonthlyTaxFact`, conserva hash por linea y
   por workbook, expone API/snapshot/admin redactados y bloquea readiness si
   faltan workbooks, faltan lineas activas, hay warnings pendientes o el
   resumen anual queda desalineado.
5. `stage6-enterprise-registers`: estructura RAI/SAC/retiros/dividendos con
   saldos iniciales y finales trazables. Implementado como
   `AnnualEnterpriseRegisterSet` y `AnnualEnterpriseRegisterMovement`: genera
   registros RAI/SAC desde lineas RLI/CPT y retiros/dividendos desde
   participaciones activas con movimientos cero trazados cuando aun no existen
   eventos propios, conserva hashes por movimiento/registro, expone
   API/snapshot/admin redactados y bloquea readiness si faltan registros,
   movimientos, resumen alineado o si existen warnings pendientes.
6. `stage6-real-estate-section`: seccion anual de bienes raices/arriendos y
   contribuciones. Implementado como `AnnualRealEstateSection` y
   `AnnualRealEstateItem`: genera items por propiedad desde `Propiedad`,
   `DistribucionCobroMensual` y `ContratoPropiedad`, distribuye arriendos por
   `porcentaje_distribucion_interna`, congela snapshots anuales con hash,
   conserva contribuciones como `not_loaded_v1`, expone API/snapshot/admin
   redactados y bloquea readiness si falta seccion, items activos, resumen
   alineado o hay warnings pendientes.
7. `stage6-ddjj-f22-artifact-matrix`: matriz DDJJ/F22 por fuente, medio,
   responsable y estado. Implementado como `AnnualTaxArtifactMatrix` y
   `AnnualTaxArtifactMatrixItem`: genera items DDJJ/F22 desde configuracion
   fiscal, `TaxCodeMapping`, `ProcesoRentaAnual`, RLI/CPT, registros
   empresariales y bienes raices; cada item conserva fuente, medio SII,
   responsable, payload no sensible, hash y `final_tax_calculation=false`.
   API/snapshot/admin redactan refs/payloads y readiness bloquea si falta
   matriz, items DDJJ/F22, resumen alineado o revision de warnings.
8. `stage6-dossier-review`: dossier anual revisable. Implementado como
   `AnnualTaxDossier`: consolida source bundle, hechos mensuales, RLI/CPT,
   registros empresariales, bienes raices y matriz DDJJ/F22 en un resumen
   hasheado con responsable, refs no sensibles, `final_tax_calculation=false`
   y `sii_submission=false`. API/snapshot/admin redactan refs/payloads y
   readiness bloquea si falta dossier, si el resumen esta desalineado, si falta
   responsable o si existen warnings/revision pendiente.
9. `stage6-export-gate`: export/preview, sin presentacion final automatica.
   Implementado como `AnnualTaxExport`: genera un paquete local controlado
   desde `AnnualTaxDossier`, source bundle, rule set y matriz DDJJ/F22, con
   payload hasheado, refs no sensibles, conteos DDJJ/F22 y flags obligatorios
   `official_format=false`, `sii_submission=false` y
   `final_tax_calculation=false`. API/snapshot/admin redactan refs/payloads y
   readiness bloquea si falta export, si el resumen esta desalineado, si hay
   revision pendiente o si intenta declarar formato oficial/presentacion/calculo
   final.

## Validaciones necesarias

| Validacion | Debe bloquear |
| --- | --- |
| Fuente anual incompleta | menos de 12 cierres aprobados, F29 faltante si aplica, ledger no cerrado |
| Hechos mensuales incompletos | proceso anual sin 12 `MonthlyTaxFact` normalizados o resumen anual desalineado |
| Regla AT ausente | cualquier calculo marcado como listo sin `TaxYearRuleSet` aprobado |
| Workbooks RLI/CPT faltantes | proceso anual trazable sin ambos workbooks preparados |
| Linea sin origen | RLI/CPT/DDJJ/F22 con monto sin fuente |
| Linea RLI/CPT con warning | requiere revision tributaria antes de cierre |
| Resumen anual RLI/CPT desalineado | hash, tipo o conteo del proceso no coincide con workbooks vigentes |
| Registros empresariales faltantes | proceso anual trazable sin RAI/SAC/retiros/dividendos preparados |
| Saldos empresariales opacos | RAI/SAC/retiros/dividendos sin saldo inicial o sin movimiento trazado |
| Resumen empresarial desalineado | hash, tipo, saldo o conteo del proceso no coincide con registros vigentes |
| Seccion bienes raices faltante | proceso anual trazable sin `AnnualRealEstateSection` preparada |
| Item bienes raices faltante | seccion anual preparada sin `AnnualRealEstateItem` activo |
| Resumen bienes raices desalineado | hash, total, monto o conteo del proceso no coincide con seccion vigente |
| Item bienes raices con warning | contribuciones u otra fuente inmobiliaria requiere revision antes de cierre |
| Matriz DDJJ/F22 faltante | proceso anual trazable sin `AnnualTaxArtifactMatrix` preparada |
| Item DDJJ/F22 faltante | matriz preparada sin items activos, sin items F22 o sin items DDJJ |
| Resumen matriz DDJJ/F22 desalineado | hash, conteos o ids del proceso no coinciden con la matriz vigente |
| Item matriz con warning/bloqueo | fuente anual requiere revision tributaria antes de package/export |
| Dossier anual faltante | proceso anual trazable sin `AnnualTaxDossier` preparado |
| Resumen dossier desalineado | hash, conteos, matriz o ids del proceso no coinciden con el dossier vigente |
| Dossier con revision pendiente | warnings o estado `requiere_revision` bloquean cierre/presentacion aunque permitan export local de revision; estado `bloqueado` impide export |
| Export anual faltante | proceso anual trazable sin `AnnualTaxExport` preparado |
| Resumen export desalineado | hash, dossier, conteos, flags o ids del proceso no coinciden con el export vigente |
| Export fuera de boundary | intento de marcar formato oficial SII, presentacion SII o calculo final autonomo |
| Responsable ausente | DDJJ/F22/dossier avanzado sin `responsable_revision_ref` |
| Refs sensibles | URLs, tokens, correos, certificados o claves en refs/payloads |
| Presentacion sin gate | intento de marcar presentado sin formato SII, autorizacion y evidencia |

## Riesgos y limites

- EDIG confirma estructura funcional, no normativa fiscal.
- Los nombres de tablas/campos observados no se portan 1:1.
- La presentacion SII queda bloqueada hasta formato/certificacion vigente.
- Renta final exige responsable tributario y revision experta/oficial.
- El motor v1 puede preparar dossier y preview; no debe sustituir criterio
  tributario profesional.
