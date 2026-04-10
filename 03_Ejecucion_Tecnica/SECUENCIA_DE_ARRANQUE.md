# Secuencia de arranque - Primer movimiento de ingenieria

## 1. Objetivo

Evitar que el primer sprint se disperse. Esta secuencia ordena que construir primero cuando todavia no existe codebase en el workspace.

## 2. Secuencia recomendada

1. Crear repositorio de codigo con estructura `backend/` y `frontend/`.
2. Inicializar backend Django 5 con settings por ambiente.
3. Inicializar frontend React + TypeScript + Vite.
4. Conectar PostgreSQL y Redis.
5. Implementar auth, RBAC y scopes base.
6. Implementar `EventoAuditable` y `ResolucionManual`.
7. Levantar Celery y healthchecks.
8. Exponer una API minima autenticada.
9. Montar shell web autenticado para backoffice.
10. Recien despues empezar `Patrimonio` y `Operacion`.

## 3. No hacer todavia

- no modelar SII antes del ledger base;
- no modelar conciliacion bancaria antes de `CuentaRecaudadora` y `MandatoOperacion`;
- no modelar contabilidad antes de tener hechos economicos del dominio;
- no construir IA ni portales;
- no escribir flujos anuales antes de que cierre mensual funcione.

## 4. Primer sprint recomendado

Sprint 1:

- `PB-01`
- `PB-02`
- `PB-03`
- `PB-04`

Sprint 2:

- `PB-05`
- `PB-06`
- `PB-07`

## 5. Senal para empezar dominio

Se puede arrancar `Patrimonio` solo cuando:

- autenticacion y roles funcionan;
- auditoria base funciona;
- backend y frontend tienen estructura estable;
- hay ambiente local reproducible para todo el equipo.
