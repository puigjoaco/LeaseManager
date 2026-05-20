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
| Patrimonio | `implementado_sin_evidencia_real` | modelos `Socio`, `Empresa`, `ComunidadPatrimonial`, `RepresentacionComunidad`, `ParticipacionPatrimonial`, `Propiedad`; APIs y tests | validar datos reales, participaciones, comunidades y activos contra fuente oficial/Excel/banco |
| Operacion | `implementado_sin_evidencia_real` | `CuentaRecaudadora`, `IdentidadDeEnvio`, `MandatoOperacion`, `AsignacionCanalOperacion`; APIs y tests | cuentas reales, identidades reales, mandatos finales y evidencias por entidad |
| Contratos | `resuelto_confirmado_local` | `Arrendatario`, `Contrato`, `ContratoPropiedad`, `PeriodoContractual`, `AvisoTermino`, `CodeudorSolidario`; validaciones y tests de contrato futuro/aviso | renovacion automatica operacional y datos contractuales reales siguen como validacion de negocio |
| CobranzaActiva | `parcial` | `ValorUFDiario`, `PagoMensual`, ajustes, garantias, repactaciones, residual, estados de cuenta; tests de UF faltante y calculo | cadena automatica UF `BancoCentral -> CMF -> MiIndicador`, WebPay/Transbank real y evidencia de cobro real |
| Conciliacion | `parcial` | `ConexionBancaria`, `MovimientoBancarioImportado`, `IngresoDesconocido`, match exacto/manual, resoluciones, tests | adapter Banco de Chile real, saldos, sync, credenciales y prueba sandbox/cuenta real |
| Contabilidad | `implementado_sin_evidencia_real` | regimen, configuracion fiscal, cuentas, reglas, matriz, eventos, asientos, obligaciones, libros, balance, cierres, reapertura; tests end-to-end locales | ledger con datos reales, saldos bancarios cuadrados, politicas finales y aprobacion contable/tributaria |
| Documentos | `parcial` | expediente, politica firma/notaria, documento emitido, formalizacion, storage_ref, checksum; tests de bloqueo por firmas/notaria | generacion PDF real, plantillas finales, storage productivo y firma/notaria operativa |
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
| 3. Renovacion por `PeriodoContractual` | `parcial` | periodos existen; falta automatizacion operativa de renovacion |
| 4. Cambio de arrendatario por termino y contrato nuevo | `parcial` | contrato futuro/aviso existe; falta flujo completo de cambio con datos reales |
| 5. Contrato retroactivo dentro de policies v1 | `implementado_sin_evidencia_real` | validaciones contractuales existen; falta escenario real documentado |
| 6. Falla provider bancario con resolucion manual | `parcial` | resolucion manual existe; falta provider real/suspension real |
| 7. Garantia completa/parcial/devolucion/retencion | `resuelto_confirmado_local` | modelos e historial con tests |
| 8. Aviso termino con contrato futuro | `resuelto_confirmado_local` | tests de aviso, contrato futuro y bloqueos |
| 9. Deuda residual con `CodigoCobroResidual` | `resuelto_confirmado_local` | modelo, APIs y tests de residual/distribucion |
| 10. Email operativo con WhatsApp suspendido | `parcial` | gate y fallback logico existen; falta envio real |
| 11. Cierre mensual con F29 preparado | `resuelto_confirmado_local` | contabilidad + SII draft cubiertos por tests |
| 12. DDJJ/F22 desde doce cierres | `resuelto_confirmado_local` | preparacion anual cubierta por tests |
| 13. SII DTE abierto y F29Presentacion cerrada | `implementado_sin_evidencia_real` | gates existen; falta integracion real y politica final |
| 14. Reverso/asiento complementario posterior a cierre | `parcial` | politica/reapertura existe; falta flujo final de reverso/asiento complementario probado end-to-end |
| 15. Exportacion sensible fuera de scope rechazada | `resuelto_confirmado_local` | compliance y permisos cubiertos por tests |
| 16. Empresa fuera de regimen soportado bloqueada | `resuelto_confirmado_local` | validacion fiscal y SII/contabilidad tienen tests |
| 17. Capacidad podada no reaparece activa | `resuelto_confirmado_local` | matriz de gates y modelo SII soportan estado `podado`; no se detecto capacidad podada activa |

## Brechas accionables priorizadas

1. `bloqueado_externo`: definir ambiente real/controlado para datos, banco,
   SII, email, WhatsApp, Vercel/Railway y secretos.
2. `parcial`: implementar adapters reales para UF, Banco de Chile, Gmail/Twilio
   y SII cuando sus gates tengan evidencia.
3. `parcial`: completar generacion PDF/storage documental; hoy existe registro
   documental y formalizacion, no motor PDF final.
4. `requiere_decision_usuario`: decidir si los `.db` y capturas versionadas en
   `backend/` y `migration/bundles/` deben moverse fuera del repo activo o
   mantenerse como evidencia historica versionada.
5. `desactualizado`: se corrigio `docs/DEPLOY_BACKEND_GREENFIELD.md`, que aun
   apuntaba a rutas antiguas `Produccion 1.0`.
6. `implementado_sin_evidencia_real`: ejecutar release gate completo en CI y
   registrar resultado antes de usar como baseline estable.

## Proximo frente recomendado

Crear un worktree `codex/phase0-release-gate-hardening` para cerrar base
tecnica: quitar/decidir artefactos versionados, verificar CI remoto, ejecutar
acceptance completa, revisar secrets inventory, endurecer deploy docs y producir
un `RELEASE_GATE_BASELINE_MAYO_2026.md`. Despues de eso corresponde empezar
`PlataformaBase`/`Patrimonio` con datos reales controlados.
