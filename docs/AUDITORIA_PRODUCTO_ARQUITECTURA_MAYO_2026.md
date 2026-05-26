# Auditoria producto-arquitectura - Mayo 2026

## Objetivo

Mapear el estado real de LeaseManager despues de promover el root limpio a
`main`, comparando el PRD canonico, gates, ADR/stack, secuencia tecnica, codigo,
migraciones, frontend, pruebas y runbooks. Esta auditoria no declara produccion:
clasifica que existe, que esta probado localmente, que depende de evidencia real
y que falta antes de uso operativo indefinido.

## Fuentes revisadas

- `01_Set_Vigente/PRD_CANONICO.md`
- `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`
- `02_ADR_Activos/*.md`
- `03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md`
- `03_Ejecucion_Tecnica/CRITERIOS_DE_SALIDA.md`
- `08_Auditoria_Stack/ADR_STACK_FINAL.md`
- apps Django en `backend/`
- workspaces React en `frontend/src/backoffice/workspaces/`
- scripts de acceptance, smoke y despliegue en `scripts/`
- workflow `.github/workflows/release-gate.yml`

## Leyenda

- `resuelto_confirmado_local`: implementado y cubierto por pruebas/gates locales.
- `implementado_sin_evidencia_real`: existe codigo y pruebas, pero falta dato,
  proveedor, credencial, ambiente o corrida real/controlada.
- `parcial`: existe una parte util, pero falta una pieza funcional del alcance.
- `bloqueado_externo`: depende de tercero, credencial, infraestructura o dato real.
- `requiere_decision_usuario`: requiere confirmar alcance, datos o politica.
- `faltante`: no se encontro implementacion suficiente.
- `desactualizado`: documento o runbook no refleja el root limpio actual.

## Estado ejecutivo

LeaseManager tiene una base greenfield coherente y amplia: Django/DRF,
PostgreSQL, Redis/Celery, React/Vite, RBAC/scopes, auditoria, dominio, migracion,
reporting y suite backend de 263 tests mapeados. No esta listo para produccion:
las integraciones reales, datos reales, cutover desde Excel/banco, despliegue
final, certificados, secrets, saldos bancarios y evidencia externa siguen sin
cerrarse. El estado correcto es: producto base avanzado, no producto final.

## Matriz por modulo

| Modulo | Estado | Evidencia encontrada | Pendiente o bloqueo |
|---|---|---|---|
| PlataformaBase | `resuelto_confirmado_local` | `users`, `core`, `audit`, `health`; token auth, roles, scopes, permisos, healthchecks; tests de auth, RBAC, scope y bootstrap | secrets productivos, storage final y hardening de ambiente real |
| Patrimonio | `implementado_sin_evidencia_real` | modelos `Socio`, `Empresa`, `ComunidadPatrimonial`, `RepresentacionComunidad`, `ParticipacionPatrimonial`, `Propiedad`; APIs, flujo auditado de transferencia/redistribucion de participaciones y tests | validar datos reales, participaciones, comunidades y activos contra fuente oficial/Excel/banco |
| Operacion | `implementado_sin_evidencia_real` | `CuentaRecaudadora`, `IdentidadDeEnvio`, `MandatoOperacion`, `AsignacionCanalOperacion`; APIs y tests | cuentas reales, identidades reales, mandatos finales y evidencias por entidad |
| Contratos | `resuelto_confirmado_local` | `Arrendatario`, `Contrato`, `ContratoPropiedad`, `PeriodoContractual`, `AvisoTermino`, `CodeudorSolidario`; validaciones, endpoints de renovacion automatica y cambio de arrendatario, tests de contrato futuro/aviso | datos contractuales reales siguen como validacion de negocio |
| CobranzaActiva | `parcial` | `ValorUFDiario` con procedencia auditada para carga manual, `PagoMensual` con efecto de codigo efectivo persistido/auditado, ajustes, garantias, repactaciones, residual, estados de cuenta; tests de UF faltante, calculo y readiness | cadena automatica UF `BancoCentral -> CMF -> MiIndicador`, WebPay/Transbank real y evidencia de cobro real |
| Conciliacion | `parcial` | `ConexionBancaria`, `MovimientoBancarioImportado`, `IngresoDesconocido`, match exacto/manual, resoluciones, tests | adapter Banco de Chile real, saldos, sync, credenciales y prueba sandbox/cuenta real |
| Contabilidad | `implementado_sin_evidencia_real` | regimen, configuracion fiscal, cuentas, reglas, matriz, eventos, asientos, obligaciones, libros, balance, cierres, reapertura; tests end-to-end locales | ledger con datos reales, saldos bancarios cuadrados, politicas finales y aprobacion contable/tributaria |
| Documentos | `parcial` | expediente, politica firma/notaria, documento emitido, emision local de PDF generado con checksum derivado, formalizacion, storage_ref, checksum; tests de bloqueo por firmas/notaria y auditoria de generacion | plantillas finales, storage productivo, prueba PDF controlada y firma/notaria operativa |
| Canales | `parcial` | gates de email/WhatsApp, identidad, preparacion/bloqueo, registro manual de envio; tests de gate suspendido y contacto bloqueado | Gmail/Twilio reales, OAuth/templates/opt-in, envio real y evidencia por identidad |
| SII | `parcial` | capacidades SII, DTE 34 draft, F29 draft, DDJJ/F22 preparacion, gates por capacidad; tests de gate cerrado/abierto y doce cierres | firma/envio/consulta real SII, certificados, ambiente, normativa validada y aprobacion final |
| Reporting | `resuelto_confirmado_local` | dashboards operativo/financiero, resumen socio, libros, anual, resoluciones manuales; workspace frontend y tests | datos reales, performance y aceptacion de usuarios |
| Compliance | `parcial` | politicas retencion, exportaciones sensibles cifradas, revoke/expiry/hold; tests | readiness legal Chile 2026, responsables, proceso formal y evidencia |
| Migracion legacy | `implementado_sin_evidencia_real` | scripts de inventario, transformacion, import, rehearsal, promote, verify; bundles y tests de pipeline | validar contra fuentes vivas, resolver artefactos versionados y decidir archivo de DB/imagenes historicas |
| Deploy/operacion | `parcial` | Dockerfile, Railway configs, Vercel docs, acceptance workflow, smoke Playwright, release-gate | URL backend final, variables, secrets, CI/checks remotos, monitoreo y runbook final |

## Matriz de acceptance del PRD

| Escenario PRD | Estado | Nota |
|---|---|---|
| 1. Contrato estandar de una propiedad | `parcial` | contrato/cobro/asiento existen localmente; falta dato real y corrida end-to-end externa |
| 2. Contrato con principal + vinculada | `resuelto_confirmado_local` | `ContratoPropiedad` y tests cubren propiedad principal/vinculada |
| 3. Renovacion por `PeriodoContractual` | `resuelto_confirmado_local` | endpoint operacional crea el tramo de renovacion, extiende vigencia, bloquea `AvisoTermino` registrado, exige politica si cambia base y deja evento auditable |
| 4. Cambio de arrendatario por termino y contrato nuevo | `resuelto_confirmado_local` | endpoint operacional crea aviso y contrato futuro con nuevo arrendatario, conserva deuda historica y deja auditoria; falta evidencia con datos reales para cierre de etapa |
| 5. Contrato retroactivo dentro de policies v1 | `implementado_sin_evidencia_real` | validaciones contractuales existen; falta escenario real documentado |
| 6. Falla provider bancario con resolucion manual | `parcial` | resolucion manual existe; falta provider real/suspension real |
| 7. Garantia completa/parcial/devolucion/retencion | `resuelto_confirmado_local` | modelos e historial con tests |
| 8. Aviso termino con contrato futuro | `resuelto_confirmado_local` | tests de aviso, contrato futuro y bloqueos |
| 9. Deuda residual con `CodigoCobroResidual` | `resuelto_confirmado_local` | modelo, APIs y tests de residual/distribucion |
| 10. Email operativo con WhatsApp suspendido | `parcial` | gate y fallback logico existen; falta envio real |
| 11. Cierre mensual con F29 preparado | `resuelto_confirmado_local` | contabilidad + SII draft cubiertos por tests |
| 12. DDJJ/F22 desde doce cierres | `resuelto_confirmado_local` | preparacion anual cubierta por tests |
| 13. SII DTE abierto y F29Presentacion cerrada | `implementado_sin_evidencia_real` | gates existen; falta integracion real y politica final |
| 14. Reverso/asiento complementario posterior a cierre | `implementado_sin_evidencia_real` | reapertura exige politica activa, efecto contable posterior (`reverso` o `asiento_complementario`), motivo, efecto esperado, evidencia no sensible y evento contabilizado bajo regla/matriz activa; falta validacion con fuente autorizada/controlada final |
| 15. Exportacion sensible fuera de scope rechazada | `resuelto_confirmado_local` | compliance y permisos cubiertos por tests |
| 16. Empresa fuera de regimen soportado bloqueada | `resuelto_confirmado_local` | validacion fiscal y SII/contabilidad tienen tests |
| 17. Capacidad podada no reaparece activa | `resuelto_confirmado_local` | matriz de gates y modelo SII soportan estado `podado`; no se detecto capacidad podada activa |

## Brechas accionables priorizadas

1. `resuelto_confirmado`: PRD Canonico Mayo 2026 aceptado y promovido a
   `01_Set_Vigente/PRD_CANONICO.md`.
2. `bloqueado_externo`: definir ambiente real/controlado para datos, banco,
   SII, email, WhatsApp, Vercel/Railway y secretos.
3. `parcial`: implementar adapters reales para UF, Banco de Chile, Gmail/Twilio
   y SII cuando sus gates tengan evidencia.
4. `parcial`: completar storage documental/productivo y plantillas finales; ya
   existe emision local controlada de PDF generado, registro documental y
   formalizacion.
5. `resuelto_en_hardening`: los `.db` locales, capturas versionadas y handoffs
   historicos del root anidado se sacaron del repo activo; quedan recuperables
   desde savegame/historial, no como producto vivo.
6. `desactualizado`: se corrigio `docs/DEPLOY_BACKEND_GREENFIELD.md`, que aun
   apuntaba a rutas antiguas `Produccion 1.0`.
7. `resuelto_confirmado_local`: el release gate deterministico quedo separado
   del smoke publico manual y fue validado en CI.
8. `parcial`: consolidar la capa de gobierno, arquitectura, plan trazable,
   stage cards, evidencia y bloqueos para continuar sin depender de memoria de
   conversacion.

## Proximo frente recomendado

Avanzar Etapa 1 con datos reales o snapshot controlado: matriz
contrato-propiedad-cuenta-facturacion, entidades patrimoniales, mandatos,
cuentas, contratos, periodos y garantias. Mantener integraciones externas
cerradas hasta cumplir gates.
