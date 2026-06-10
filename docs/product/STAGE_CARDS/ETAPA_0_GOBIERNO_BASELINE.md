# Etapa 0 - Gobierno y baseline

## Objetivo

Dejar claro que manda, como se trabaja, cual es el baseline tecnico y que
evidencia respalda el root limpio.

## Entradas

- `AGENTS.md`
- `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`
- `docs/governance/CODEX_OPERATING_PROTOCOL_MAYO_2026.md`
- `docs/product/EXECUTION_CURSOR_MAYO_2026.md`
- `docs/RELEASE_GATE_BASELINE_MAYO_2026.md`
- CI en `main`

## Gate

- Fuente de verdad sin ambiguedad.
- Worktree policy documentada.
- Cursor operativo vigente para reanudaciones, worktrees y metatareas cerradas.
- Artefactos locales de herramienta quedan fuera del versionado y no deben
  ensuciar `git status` del root limpio ni confundirse con paquete activo:
  `.codex-spreadsheet/`, `.playwright-cli/`, capturas PNG en el root y
  archivos manuales marcados `CONFIDENCIAL`/`NO_SUBIR` quedan ignorados sin
  leer su contenido; acceptance ejecuta `assert-repo-hygiene.ps1
  -IncludeUntracked` para detectar nuevos artefactos sensibles no ignorados.
- Superficies publicas con errores seguros, sin mensajes internos ni nombres de
  configuracion expuestos.
- Auth no expone metadata de usuario sensible: login, login demo y `/me`
  devuelven metadata redactada, la firma interna de cache demo no viaja al
  cliente y el admin muestra metadata y `legacy_reference` solo redactados, sin
  permitir borrado manual de usuarios.
- Login y logout persistente mantienen tokens y auditoria en una unica
  transaccion: si falla `auth.login.succeeded`, no queda token creado; si falla
  `auth.logout`, no queda token eliminado sin traza.
- El detector transversal de referencias sensibles redacta valores y claves de
  metadata como `authorization` y `private_key`, sin tratar refs operativas no
  sensibles como secretos por su nombre de valor.
- Auditoria no expone referencias sensibles heredadas en API ni snapshot:
  eventos redactan actor, entidad, resumen, request id y metadata; las
  resoluciones manuales redactan scope, resumen, rationale y metadata, y la API
  generica rechaza nuevas escrituras con referencias sensibles.
- Las resoluciones manuales genericas conservan actor de solicitud y cierre
  trazable: la API crea casos abiertos con `requested_by` del usuario actual,
  no acepta cierres al crear, exige rationale para cerrar y estampa
  `resolved_by`/`resolved_at` desde el usuario autenticado.
- Las resoluciones manuales genericas registran eventos de ciclo de vida en la
  misma transaccion que la escritura: creacion, cambios de estado y ediciones
  comunes crean `AuditEvent` dedicado, y si falla esa auditoria se revierte la
  creacion o mutacion.
- El admin Django de Auditoria es solo lectura para eventos y resoluciones
  manuales: no permite alta, cambio ni borrado manual, y conserva campos
  crudos sensibles solo como versiones redactadas.
- Los admins RBAC de Core no exponen metadata ni permission sets crudos y no
  permiten borrado manual de roles, scopes, permisos por scope ni asignaciones.
- `PlatformSettingAdmin` muestra valores de plataforma solo redactados y no
  permite alta ni borrado manual de settings existentes.
- `PlatformSetting` valida en dominio el control
  `security.admin_mfa_control`: debe declarar MFA administrativo probado o
  aceptacion formal de riesgo vigente, siempre con evidencia, autorizacion y
  responsable no sensibles.
- Compliance de datos sensibles trata exportaciones expiradas como terminales:
  no se descargan, no se revocan, una exportacion ya revocada no se revoca de
  nuevo y las exportaciones preparadas vencidas sin hold se normalizan a
  `expirada` antes de rechazar operaciones terminales incompatibles.
- La descarga de exportaciones sensibles y la revocacion denegada de
  exportaciones preparadas ya vencidas se ejecutan dentro de la misma
  transaccion que sus eventos `accessed` o `access_denied` y cualquier
  normalizacion terminal de estado; si falla la auditoria de acceso denegado,
  no queda una exportacion marcada `expirada` sin traza.
- La readiness de Compliance valida la metadata historica de eventos de
  exportacion sensible sin convertir cambios posteriores de estado en falsos
  positivos: `prepared` y `accessed` conservan estado `preparada`, `revoked`
  conserva `revocada` y `access_denied` conserva el estado observado al negar
  el acceso.
- Compliance no expone `evento_inicio` sensible heredado de politicas de
  retencion en API ni admin: nuevas escrituras siguen bloqueadas por dominio y
  los valores heredados se representan redactados. El admin de politicas y
  exportaciones sensibles mantiene cerrados el alta, edicion y borrado manual:
  las mutaciones deben pasar por API, servicios, dominio y auditoria.
- Las altas y ediciones API de politicas de retencion persisten la politica y
  los eventos `created`, `updated` o `state_changed` dentro de una unica
  transaccion; si falla la auditoria de vista, no queda una politica creada o
  mutada sin traza.
- Los eventos `compliance.politica_retencion.state_changed` deben conservar
  metadata minima de transicion con `campo_estado`, `estado_anterior` y
  `estado_nuevo`.
- `audit_compliance_data_readiness` bloquea eventos `state_changed` heredados
  de Compliance que no conserven esa metadata minima de transicion.
- Compliance de datos sensibles permite a `RevisorFiscalExterno` preparar y
  descargar exportaciones sensibles solo dentro de un scope explicito asignado:
  el payload se renderiza con `ScopeAccess`, detalle/descarga/revocacion
  revalidan el scope actual, los intentos fuera de scope se rechazan y los
  usuarios no administradores solo ven/operan sus propias exportaciones.
- La preparacion y revocacion de exportaciones sensibles crean los eventos
  `compliance.exportacion_sensible.prepared` y
  `compliance.exportacion_sensible.revoked` desde el servicio y en la misma
  transaccion que persiste el estado, evitando exportaciones sensibles sin
  auditoria dedicada si falla la escritura del evento. La preparacion desde
  servicio exige motivo operativo y actor creador trazable; la revocacion desde
  servicio tambien exige motivo operativo no sensible y actor trazable antes
  de persistir la revocacion.
- El backoffice de Compliance muestra motivo y scope visible ya redactados de
  exportaciones sensibles, exige motivo no sensible antes de revocar y envia
  ese motivo a la API para que quede persistido como `revocation_reason`.
- Los comandos demo de Compliance no repiten referencias o alcances operativos
  crudos en stdout: el bootstrap de politicas solo confirma
  `evento_inicio_validado=true` y el bootstrap de exportaciones resume el scope
  por cantidad de campos, manteniendo ids, `evento_inicio` y `scope_resumen`
  fuera de la salida humana.
- El seed demo de acceso RBAC no repite usernames, codigos de scope, nombres
  de socio, ids ni referencias operativas crudas en stdout: conserva la
  creacion de usuarios, roles, scopes y asignaciones, pero reporta solo indice
  demo, rol, tipo de scope, presencia booleana de referencia y password no
  impreso.
- CI deterministica verde.
- Savegames preservados read-only.
- Registro de evidencia inicial actualizado.

## Salida

Estado minimo: `resuelto_confirmado` para gobierno base. El PRD Mayo 2026 ya
esta promovido como rector; cualquier nueva decision de producto debe
registrarse como cambio al PRD vigente o bloqueo concreto.
