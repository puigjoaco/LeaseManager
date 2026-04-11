# Borrador Actual

## 1. Situacion actual del “borrador”

No existe un nuevo documento único que reemplace al código como entregable principal del tramo actual.

El entregable vigente hoy es una combinación de:

- set canónico (`PRD`, `ADR`, roadmap);
- implementación real del backoffice;
- permisos RBAC efectivos en backend;
- seed demo y hardening inicial de scope.

Por eso, para esta etapa, “borrador actual” significa:

- **base de trabajo vigente para continuar el siguiente thread**

## 2. Ranking de piezas vigentes hoy

### Ranking 1

[D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)

Motivo:

- sigue siendo la fuente primaria de producto, dominio y permisos críticos;
- fija actores, restricciones, acceptance y boundary.

### Ranking 2

[D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)  
[D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)

Motivo:

- hoy son la mejor base para entender qué ya se cubrió y por qué el siguiente paso ya no es “otro módulo base”.

### Ranking 3

[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)

Motivo:

- concentra el estado real del backoffice;
- si hay duda sobre qué ya existe en UI, esta pieza manda.

### Ranking 4

[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_permissions.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py)

Motivo:

- definen, siembran y prueban el estado actual de RBAC + scope efectivo del backend;
- son base obligatoria para cualquier trabajo nuevo sobre validación manual de perfiles o permisos finos.

### Ranking 5

[D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)

Motivo:

- sigue siendo la base principal para el subdominio comunitario ya cerrado;
- no debe ser reemplazada para ese problema, aunque ya no sea el foco del siguiente paso.

## 3. Estado del borrador/entregable principal

Estado actual:

- no hay un solo documento nuevo pendiente de cierre para esta etapa;
- la base principal de continuidad ya es mayormente código;
- el proyecto está en una fase de endurecimiento operativo y de validación por perfil.

## 4. Base a usar en el siguiente thread

Usar como base principal, en este orden:

1. [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)
2. [ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)
3. [MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)
4. [App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)
5. [permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)
6. [scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)
7. [seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)
8. [tests_permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_permissions.py)
9. [tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py)
10. [01_CONTEXTO_MAESTRO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/01_CONTEXTO_MAESTRO.md)
11. [04_DECISIONES_VIGENTES.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/04_DECISIONES_VIGENTES.md)
12. [03_CRONOLOGIA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/03_CRONOLOGIA.md)

Para cualquier consulta puntual sobre el dominio comunitario ya cerrado, reinyectar además:

13. [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)
