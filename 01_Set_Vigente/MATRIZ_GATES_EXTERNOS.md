# Matriz de gates externos - LeaseManager

Estado: vigente  
Fecha: 15/03/2026  
Documento rector relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## 1. Regla de uso

Esta matriz define si una capacidad externa puede operar en modo:

- `Abierto`: la capacidad puede operar automaticamente segun su flujo.
- `Condicionado`: la capacidad puede existir en el producto, pero requiere validacion activa por tenant, cuenta o empresa.
- `Cerrado`: la capacidad no se ofrece como automatizacion activa.
- `Podado`: la capacidad queda fuera del boundary activo del v1 y no debe leerse como compromiso vigente.
- `Suspendido`: la capacidad estaba habilitada y quedo temporalmente fuera de servicio.

Ningun roadmap ni promesa comercial puede abrir una capacidad si su gate sigue cerrado.

## 2. Gates bancarios

| Capacidad | Provider inicial | Estado default | Entrada | Suspension | Salida | Fallback permitido | Evidencia minima |
|---|---|---|---|---|---|---|---|
| `Banca.Movimientos` | `BancoDeChile` | `Condicionado` | credenciales oficiales validas, conectividad sana, cuenta marcada operativa, primer sync exitoso | autenticacion rechazada, proveedor caido, scopes insuficientes, credencial vencida | sync exitoso verificado y validacion de salud | carga y asignacion manual auditada | prueba end-to-end sobre cuenta real o sandbox aprobada |
| `Banca.Saldos` | `BancoDeChile` | `Condicionado` | misma base de `Banca.Movimientos` mas lectura de saldo validada | errores repetidos o datos inconsistentes | lectura correcta posterior y validacion humana o automatica | consulta manual externa con evidencia | muestra de saldo consistente contra origen bancario |
| `Banca.Conectividad` | `BancoDeChile` | `Condicionado` | validacion positiva del adapter y del secreto activo | timeouts sostenidos o credencial invalida | healthcheck exitoso en ventana operativa | alerta y operacion manual | healthcheck registrado y monitoreado |

## 3. Gates UF

| Capacidad | Fuente inicial | Estado default | Entrada | Suspension | Salida | Fallback permitido | Evidencia minima |
|---|---|---|---|---|---|---|---|
| `UF.BancoCentral` | `BancoCentral` | `Condicionado` | fuente accesible y dato consistente | caida, formato invalido, dato ausente | lectura correcta posterior | pasar a `CMF` | valor validado contra mes operativo |
| `UF.CMF` | `CMF` | `Condicionado` | fuente accesible y dato consistente | caida o inconsistencia | lectura correcta posterior | pasar a `MiIndicador` | valor validado contra fuente primaria o historico reciente |
| `UF.MiIndicador` | `MiIndicador` | `Condicionado` | fuente accesible y dato consistente | caida o inconsistencia | lectura correcta posterior | carga manual auditada | valor validado por operador responsable |
| `UF.CargaManualExtraordinaria` | `Humano` | `Abierto` | falla completa de fuentes automaticas y aprobacion auditada | dato manual observado como incorrecto | rectificacion auditada | no aplica | usuario, fecha, motivo y valor persistidos |

## 4. Gates de comunicacion

| Capacidad | Provider inicial | Estado default | Entrada | Suspension | Salida | Fallback permitido | Evidencia minima |
|---|---|---|---|---|---|---|---|
| `Email.Salida` | `GmailAPI` | `Condicionado` | `IdentidadDeEnvio` activa, OAuth valido, prueba de envio satisfactoria | token revocado, quota agotada, error persistente de envio | renovacion de token y prueba satisfactoria | alerta al administrador y reintento manual controlado | envio y recepcion de prueba por identidad |
| `WhatsApp.Salida` | `TwilioWhatsApp` | `Condicionado` | numero habilitado, templates aprobados, canal no bloqueado, opt-in operativo | bloqueo del canal, rechazo de template, error definitivo del provider | nueva prueba satisfactoria y desbloqueo operativo | email si esta disponible; si no, alerta critica | envio correcto con template vigente |

## 5. Gates SII por capacidad

| Capacidad | Provider inicial | Estado default | Entrada | Suspension | Salida | Fallback permitido | Evidencia minima |
|---|---|---|---|---|---|---|---|
| `SII.DTEEmision` | `SII` | `Condicionado` | empresa habilitada, `ConfiguracionFiscalEmpresa` completa, certificado vigente, ambiente valido, prueba exitosa del flujo | certificado invalido, error sistematico, cambio normativo sin validar | nueva prueba exitosa y credenciales regularizadas | borrador + operacion manual controlada | emision de prueba validada |
| `SII.DTEConsultaEstado` | `SII` | `Condicionado` | acceso valido y consulta exitosa | rechazo repetido, ambiente invalido | consulta exitosa posterior | consulta manual con evidencia | consulta trazada contra documento real |
| `SII.BoletaEmision` | `SII` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | manual fuera de plataforma | fuera del boundary activo |
| `SII.LibrosYArchivos` | `SII` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | generacion asistida offline fuera del core | fuera del boundary activo |
| `SII.F29Preparacion` | `SII` | `Condicionado` | cierre mensual aprobado, `ConfiguracionFiscalEmpresa` vigente, certificado vigente, flujo de borrador probado | cambio normativo, fallo sistematico o cierre inconsistente | nueva validacion con cierre mensual correcto | borrador manual controlado | borrador validado contra caso real |
| `SII.F29Presentacion` | `SII` | `Condicionado` | `F29Preparacion` valida, gate especifico abierto y politica de aprobacion vigente | cambio normativo, error de presentacion o gate sin readiness | reapertura formal y prueba exitosa | presentacion manual externa con evidencia | simulacion end-to-end aprobada |
| `SII.DDJJPreparacion` | `SII` | `Condicionado` | proceso anual aprobado, `ConfiguracionFiscalEmpresa` vigente, mapeo de DDJJ vigente, flujo de borrador probado | cambio normativo, datos anuales inconsistentes | reapertura con validacion anual | borrador y checklist manual | paquete anual de prueba consistente |
| `SII.F22Preparacion` | `SII` | `Condicionado` | proceso anual aprobado, `ConfiguracionFiscalEmpresa` vigente, mapeo tributario vigente, borrador probado | cambio normativo, inconsistencias anuales o fallo sistematico | reapertura con validacion anual | borrador y revision manual | borrador anual trazado contra datos de ledger |
| `SII.PresentacionAnualFinal` | `SII` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | operacion manual controlada fuera del core | fuera del boundary activo |

## 6. Gates regulatorios internos

| Capacidad | Provider inicial | Estado default | Entrada | Suspension | Salida | Fallback permitido | Evidencia minima |
|---|---|---|---|---|---|---|---|
| `Compliance.DatosPersonalesChile2026` | `Interno` | `Condicionado` | politica aprobada, responsables designados, controles implementados y evidencia archivada | ausencia de readiness, incumplimiento detectado o cambio normativo no absorbido | nueva validacion legal-operativa | suspension de produccion posterior al `01/12/2026` | checklist formal aprobada y trazada |

## 7. Capacidades podadas del boundary activo

| Capacidad | Provider inicial | Estado default | Entrada | Suspension | Salida | Fallback permitido | Evidencia minima |
|---|---|---|---|---|---|---|---|
| `Portales.PortalInmobiliario` | `PortalInmobiliario` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | checklist manual fuera del core | fuera del boundary activo |
| `Portales.Yapo` | `Yapo` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | checklist manual fuera del core | fuera del boundary activo |
| `IA.ClasificacionDocumental` | `LLMProviderAprobado` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | clasificacion manual | fuera del boundary activo |
| `IA.Semantica` | `PostgreSQL+pgvector` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | busqueda transaccional | fuera del boundary activo |
| `IA.AsistenteConversacional` | `LLMProviderAprobado` | `Podado` | no aplica en v1 | no aplica | solo por reemision formal del set | consultas manuales y reportes tradicionales | fuera del boundary activo |

## 8. Regla final

Una capacidad externa solo puede marcarse como `Abierto` o `Condicionado` cuando la evidencia minima exista y quede trazada. Si la evidencia desaparece, el gate vuelve a `Cerrado` o `Suspendido` segun corresponda. Una capacidad `Podada` no puede reactivarse sin reemision formal del set activo.

