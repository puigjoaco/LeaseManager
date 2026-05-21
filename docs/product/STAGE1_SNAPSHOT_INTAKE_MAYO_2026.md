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
- Confirmacion explicita si el entorno permite migraciones. Para bases reales,
  no se ejecutan migraciones desde este gate.

## Reglas

- No imprimir ni commitear `DATABASE_URL`, dumps, certificados o snapshots.
- Si el output queda dentro del repo, debe quedar bajo `local-evidence/`, que no
  se versiona.
- Para SQLite local, una URL relativa como
  `sqlite:///local-evidence/stage1/snapshot.sqlite3` se resuelve contra el root
  limpio antes de cambiar al directorio `backend`.
- `snapshot_controlado` puede usar `-RunMigrations` solo si es un clon o base
  temporal preparada para este gate.
- `real_autorizado` debe estar previamente migrado y accesible en modo
  autorizado; este script falla si se intenta migrarlo.
- Un resultado fallido se registra como bloqueo o defecto, no como avance
  cerrado.
- El auditor Django tambien bloquea fuentes evidenciales sin `SourceLabel`
  trazable o con etiqueta que parezca URL, secreto, token, email o RUT; si una
  etiqueta invalida llega al JSON, se redacta antes de escribirla.

## Comando recomendado

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 `
  -SourceKind snapshot_controlado `
  -SourceLabel "stage1-mayo-2026-v1" `
  -RunMigrations
```

Para una fuente real ya migrada:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 `
  -SourceKind real_autorizado `
  -SourceLabel "stage1-real-autorizado-mayo-2026"
```

Si se ejecuta desde un worktree sin `backend/.venv`, agregar `-PythonExe` con
la ruta al Python autorizado del root limpio.

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
`SourceLabel`, comando, resultado y ubicacion segura del JSON. No pegar datos
sensibles en la evidencia.
