# Auditoria documental post-merge - Mayo 2026

## Alcance

Auditoria inicial ejecutada despues de mergear el root limpio a `main` mediante
el PR #2. El objetivo es separar documentos operativos vigentes de trazabilidad
historica y corregir referencias que todavia hablaban como si el root limpio no
hubiese sido promovido.

## Hallazgos corregidos

- `README.md` aun indicaba que la rama activa era
  `codex/root-clean-integration`; se actualizo a `main`.
- `AGENTS.md` aun trataba la rama de integracion como estado diario; se
  actualizo la regla base a `main` y worktrees tacticos por frente.
- `AGENTS.md` tenia una frase ambigua sobre "root actual"; se corrigio para
  apuntar al root historico/savegame.
- Runbooks operativos conservaban rutas `Produccion 1.0`; se actualizaron las
  rutas que hoy deben ejecutarse desde `D:/Proyectos/LeaseManager`.
- El runbook de swap quedo marcado como historico ejecutado, no como instruccion
  cotidiana.
- Handoffs pre-merge y plan de ordenamiento quedaron marcados como documentos
  historicos o antecedentes para no confundirlos con el estado operativo actual.

## Hallazgos no corregidos por diseno

- `05_Contexto_Historico/` conserva menciones a `CLAUDE.md`, Claude, PRD
  intermedios y rutas antiguas porque es trazabilidad historica.
- Los documentos de auditoria de fuentes conservan menciones a TaskMaster,
  Claude, Next.js y Supabase cuando explican origen, descarte o contexto.
- No se reescriben PRD historicos para evitar destruir evidencia de origen.

## Regla resultante

La documentacion viva debe referirse al root limpio actual y a `main`. Las
referencias a herramientas o carpetas heredadas solo son validas si estan
marcadas como historia, respaldo, descarte, fuente de contraste o savegame.
