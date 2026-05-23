# Intake controlado de snapshot - Etapa 1

Este procedimiento desbloquea `BLK-002` sin exponer secretos ni declarar cierre
por evidencia local. Solo sirve para validar la matriz
contrato-propiedad-cuenta-facturacion contra `snapshot_controlado` o
`real_autorizado`.

## Entradas obligatorias

- `DATABASE_URL` o `-DatabaseUrl` apuntando a una fuente autorizada.
- `SourceKind`: `snapshot_controlado` o `real_autorizado`.
- `SourceLabel`: etiqueta no sensible, sin URL, RUT, token, password ni dato
  bancario.
- `AuthorizationRef`: referencia no sensible a la autorizacion concreta de uso
  de la fuente.
- `ResponsibleRef`: referencia no sensible al responsable operativo del gate o
  de la fuente.
- Confirmacion explicita si el entorno permite migraciones. Para bases reales,
  no se ejecutan migraciones desde este gate.

## Reglas

- No imprimir ni commitear `DATABASE_URL`, dumps, certificados o snapshots.
- Si el output queda dentro del repo, debe quedar bajo `local-evidence/`, que no
  se versiona. El wrapper y el comando Django rechazan rutas de `--output`
  dentro del repo que no esten bajo `local-evidence/`.
- Para SQLite local, una URL relativa como
  `sqlite:///local-evidence/stage1/snapshot.sqlite3` se resuelve contra el root
  limpio antes de cambiar al directorio `backend`.
- `snapshot_controlado` puede usar `-RunMigrations` solo si es un clon o base
  temporal preparada para este gate.
- `real_autorizado` debe estar previamente migrado y accesible en modo
  autorizado; este script falla si se intenta migrarlo.
- Un resultado fallido se registra como bloqueo o defecto, no como avance
  cerrado.
- El auditor Django tambien bloquea fuentes evidenciales sin `SourceLabel`,
  `AuthorizationRef` y `ResponsibleRef` trazables, o con valores que parezcan
  URL, secreto, token, credencial, email o RUT; si un valor invalido llega al
  JSON, se redacta antes de escribirlo.

## Comando recomendado

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 `
  -SourceKind snapshot_controlado `
  -SourceLabel "stage1-mayo-2026-v1" `
  -AuthorizationRef "autorizacion-stage1-mayo-2026" `
  -ResponsibleRef "responsable-stage1-operacion" `
  -RunMigrations
```

Para una fuente real ya migrada:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 `
  -SourceKind real_autorizado `
  -SourceLabel "stage1-real-autorizado-mayo-2026" `
  -AuthorizationRef "autorizacion-real-stage1-mayo-2026" `
  -ResponsibleRef "responsable-stage1-real"
```

Si se ejecuta desde un worktree sin `backend/.venv`, agregar `-PythonExe` con
la ruta al Python autorizado del root limpio.

## Verificacion local sin fuente autorizada

Cuando no existe `DATABASE_URL` autorizado, no se debe repetir la misma
solicitud de desbloqueo. Para avanzar en preparacion segura, ejecutar el
readiness local:

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage1-local-readiness.ps1
```

Este comando crea una SQLite vacia bajo `local-evidence/` y ejecuta el auditor
con `source_kind=local`, sin `--require-data` y sin `--fail-on-violations`. El
resultado esperado es `classification=implementado_sin_evidencia`,
`evidence_grade=false` y `ready_for_stage1_close=false`.

El acceptance deterministico ejecuta este readiness local para comprobar que la
preparacion segura no solicita secretos ni simula una fuente controlada. El
bloqueo `stage1.data_missing` queda reservado para el gate evidencial
`run-stage1-snapshot-gate.ps1`, que solo acepta `snapshot_controlado` o
`real_autorizado` con referencias trazables. El mismo acceptance tambien
protege que `real_autorizado` con `-RunMigrations` falle antes de generar JSON:
las migraciones desde este wrapper solo corresponden a clones
`snapshot_controlado` preparados para el gate.

## Criterio de cierre

El JSON de salida debe indicar:

- `has_required_stage1_data: true`
- `evidence_grade: true`
- `ready_for_stage1_close: true`
- `issue_counts.blocking` ausente o `0`
- `classification: resuelto_confirmado`
- `aggregate_classification` con cada agregado requerido en
  `classification: resuelto_confirmado`

Si falla por `stage1.data_missing`, el estado sigue `bloqueado_dato_real`. Si
falla por otras reglas, se clasifica como `defectuoso` y debe corregirse la
fuente, transformacion o modelo antes de repetir el gate.

## Registro posterior

Despues de un resultado valido, registrar en
`docs/product/EVIDENCE_REGISTER_MAYO_2026.md` la fecha, `SourceKind`,
`SourceLabel`, `AuthorizationRef`, `ResponsibleRef`, comando, resultado y
ubicacion segura del JSON. No pegar datos sensibles en la evidencia.
