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
| `MonthlyTaxFact` | Normalizar hechos mensuales | F29, cierre mensual, liquidaciones, pagos | base mensual anualizable | periodo cerrado |
| `AnnualTaxNormalizer` | Transformar fuentes a registros intermedios | source bundle + rule set | RLI, CPT, RAI, SAC, DDJJ base | no calcula sin rule set vigente |
| `RliWorkbook` | Determinar lineas RLI trazadas | ingresos/gastos/ajustes | lineas RLI, warnings | ajustes con fuente |
| `CptWorkbook` | Determinar capital propio tributario | balance, activos, pasivos, patrimonio | lineas CPT y razonabilidad | plan de cuentas clasificado |
| `EnterpriseRegisterSet` | Construir RAI/SAC/retiros/dividendos | RLI/CPT/socios/movimientos | registros empresariales | saldos iniciales trazados |
| `RealEstateAnnualSection` | Normalizar bienes raices/arriendos | propiedades, contratos, pagos, contribuciones | seccion anual y respaldo | fuente SII/experta para codigos |
| `DdjjPackageBuilder` | Preparar DDJJ/certificados | registros, socios, certificados | paquetes DDJJ revisables | medio SII vigente por formulario |
| `F22DraftBuilder` | Mapear a codigos F22 | registros intermedios y DDJJ | preview F22 | formato/certificacion vigente |
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
   `TaxCodeMapping`, sin formulas finales.
2. `stage6-source-bundle`: congelar fuentes anuales desde cierres/F29/ledger
   controlados.
3. `stage6-monthly-tax-facts`: crear hechos mensuales anualizables desde F29,
   pagos, liquidaciones y cierres.
4. `stage6-rli-cpt-skeleton`: estructura RLI/CPT con lineas trazadas y
   warnings, sin afirmar calculo fiscal final.
5. `stage6-enterprise-registers`: estructura RAI/SAC/retiros/dividendos con
   saldos iniciales y finales trazables.
6. `stage6-real-estate-section`: seccion anual de bienes raices/arriendos y
   contribuciones.
7. `stage6-ddjj-f22-artifact-matrix`: matriz DDJJ/F22 por fuente, medio,
   responsable y estado.
8. `stage6-dossier-review`: dossier anual revisable con bloqueo si falta
   responsable.
9. `stage6-export-gate`: export/preview, sin presentacion final automatica.

## Validaciones necesarias

| Validacion | Debe bloquear |
| --- | --- |
| Fuente anual incompleta | menos de 12 cierres aprobados, F29 faltante si aplica, ledger no cerrado |
| Regla AT ausente | cualquier calculo marcado como listo sin `TaxYearRuleSet` aprobado |
| Linea sin origen | RLI/CPT/DDJJ/F22 con monto sin fuente |
| Saldos empresariales opacos | RAI/SAC sin saldo inicial o sin movimiento trazado |
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
