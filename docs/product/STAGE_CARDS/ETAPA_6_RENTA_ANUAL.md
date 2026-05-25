# Etapa 6 - Renta anual

## Objetivo

Preparar proceso anual de renta, DDJJ, F22, certificados y trazabilidad desde
cierres mensuales.

## Alcance

- Proceso de renta anual.
- Certificados.
- Declaraciones juradas.
- F22 y respaldos.
- Validaciones tributarias.

## Gate

- Cierres mensuales completos.
- Reglas tributarias validadas.
- Documentos generados desde datos trazables.
- Evidencia sin datos sensibles expuestos.
- Capacidades DDJJ/F22, ProcesoRentaAnual, DDJJ y F22 pertenecen a empresas
  con `ConfiguracionFiscalEmpresa` activa propia; el dominio/API rechaza
  nuevas escrituras que no cumplan esa regla.
- `audit_stage6_renta_anual_readiness` consolida configuracion fiscal,
  capacidades DDJJ/F22, doce cierres, obligaciones mensuales, proceso anual,
  respaldos tributarios PDF y referencias finales no sensibles sin conectar SII
  ni leer certificados reales.
- `ProcesoRentaAnual.resumen_anual`, `DDJJPreparacionAnual.resumen_paquete`
  y `F22PreparacionAnual.resumen_f22` deben trazar al ano comercial
  inmediatamente anterior al `anio_tributario`; el dominio rechaza nuevas
  escrituras desalineadas y readiness bloquea snapshots heredados.
- El dominio SII rechaza F29, ProcesoRentaAnual, DDJJ y F22 en estados
  aprobados, presentados, observados o rectificados si falta la referencia
  final trazable correspondiente.
- El dominio SII tambien rechaza ProcesoRentaAnual, DDJJ y F22 asociados a
  empresas sin `ConfiguracionFiscalEmpresa` activa propia.
- Los payloads anuales y referencias de DDJJ/F22 heredadas se entregan a
  reporting con redaccion antes de exponerse al backoffice.
- `audit_stage6_renta_anual_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Etapa 6.
- Una fuente evidencial debe incluir `--source-label` y
  `--authorization-ref` no sensibles. Sin esas refs, el tipo de fuente queda
  reconocido pero no puede cerrar Etapa 6.
- `scripts/run-stage6-readiness-gate.ps1` ejecuta el diagnostico local con
  SQLite efimero bajo `local-evidence/`, no conecta SII, no lee `.env`, no usa
  certificados y reserva `-RequireReady` para fuentes autorizadas con refs
  trazables de Etapa 5, Etapa 4 SII, regla fiscal, certificados y responsable.

```powershell
scripts\run-stage6-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

La renta anual no cierra si existen meses sin cierre validado o reglas fiscales
sin respaldo.
