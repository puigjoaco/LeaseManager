# Borrador Actual

## 1. Documento principal vigente

Base principal hoy:

[D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)

Rol:

- borrador tecnico vigente;
- especificacion principal usada para implementar el backend;
- base principal para continuar cualquier ejecucion real del pipeline.

## 2. Ranking de piezas para este tema

### Ranking 1

`ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md`

Motivo:

- es la pieza mas actual;
- incorpora decisiones ya cerradas por el usuario;
- ya fue usada para cambios efectivos de codigo;
- refleja el estado real actual del backend.

### Ranking 2

`migration/enrichments.py`

Motivo:

- concentra la verdad de negocio actual que el legacy no trae por si solo;
- es indispensable para reproducir la corrida de inspeccion final;
- sin esta pieza, el bundle regenerado no refleja cartera actual ni casos confirmados como `Edificio Q` o `Paulina -> 97`.

### Ranking 3

`AUDITORIA_DISENO_COMUNIDADES_Y_RECAUDACION_2026-04-05.md`

Motivo:

- sigue siendo la mejor pieza para entender por que se llego a este diseño;
- pero ya no es la base principal para ejecutar trabajo nuevo.

### Ranking 4

Implementacion actual (`backend/*`, `migration/*`)

Motivo:

- contiene la verdad executable real;
- debe leerse despues de la especificacion y los enriquecimientos.

## 3. Estado del borrador

Estado actual del borrador principal:

- argumentado;
- implementado en backend;
- validado por pruebas en SQLite;
- validado por corrida de inspeccion del pipeline;
- no formalizado aun como ADR nuevo.

## 4. Base a usar en el siguiente thread

Usar como base principal, en este orden:

1. [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)
2. [migration/enrichments.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/enrichments.py)
3. [01_CONTEXTO_MAESTRO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/01_CONTEXTO_MAESTRO.md)
4. [04_DECISIONES_VIGENTES.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/04_DECISIONES_VIGENTES.md)
5. [03_CRONOLOGIA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/03_CRONOLOGIA.md)
