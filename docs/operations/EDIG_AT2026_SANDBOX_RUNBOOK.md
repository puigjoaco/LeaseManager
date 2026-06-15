# Runbook sandbox EDIG AT2026

Estado: procedimiento de investigacion controlada.

Este runbook permite observar EDIG AT2026 sin contaminar LeaseManager, sin
ejecutar binarios en el root activo y sin usar datos reales. El objetivo es
aprender el flujo funcional para disenar el motor propio de Renta Anual.

Estado posterior al contraste SII 2026-06-15: la ejecucion de EDIG no es
necesaria para continuar la arquitectura ni la implementacion de LeaseManager.
La evidencia estatica y oficial ya confirma la union
contabilidad/remuneraciones -> capa tributaria anual -> DDJJ/F22/export
revisable. Este runbook queda como procedimiento excepcional para observar UI,
mensajes de validacion o estructura de salida con datos ficticios, no para
extraer reglas, formulas, tablas propietarias ni formatos finales.

Nota: la extraccion estatica de metadata MDB con
`scripts/extract-edig-mdb-schema.ps1` no ejecuta EDIG ni lee filas, y puede
correr en el entorno local sobre copias temporales de MDB nucleo. La ejecucion
interactiva de binarios EDIG, generacion de archivos o navegacion por pantallas
queda limitada a la VM/sandbox de este runbook.

## Condicion de entrada

Solo ejecutar este runbook si una brecha concreta no puede resolverse con:

- fuentes oficiales SII;
- documentos EDIG no ejecutables;
- esquemas MDB sin filas;
- plantillas XLSX;
- manuales PDF;
- notas de version;
- reportes estaticos;
- revision experta.

La brecha debe registrarse previamente con la pregunta exacta que se quiere
observar. Si el objetivo es obtener reglas fiscales, copiar formulas o validar
presentacion real, este runbook no aplica.

## Precondiciones

- VM Windows aislada o sandbox equivalente, con snapshot previo.
- Carpeta EDIG copiada fuera del repo, por ejemplo `C:\Sandbox\EDIG_AT2026`.
- Red deshabilitada para la primera pasada.
- Sin certificados reales, sin claves SII, sin RUTs reales y sin licencias
  productivas.
- Datos ficticios: contribuyente, empresa, socios, balance, F29, retiros,
  dividendos, arriendos y contribuciones.
- Carpeta de salida monitoreada: `C:\Sandbox\EDIG_OUTPUT`.

## Flujo observado a ejecutar

1. Crear snapshot de VM.
2. Registrar hashes/tamanos de la copia EDIG.
3. Iniciar monitoreo de archivos con herramienta de la VM.
4. Ejecutar solo dentro de la VM: administrador, launcher, modulo regimen y
   Formulario 22.
5. Crear contribuyente ficticio y asignar regimen.
6. Intentar importacion/carga contable o balance con datos ficticios.
7. Completar datos minimos de RLI, CPT, RAI, SAC, socios, retiros/dividendos,
   F29/PPM y arriendos.
8. Generar preview F22/compacto/HTML si el software lo permite.
9. Generar archivo de upload/export con datos ficticios si el software lo
   permite, sin conectarse a SII.
10. Copiar solo metadatos no sensibles: nombres de archivos generados,
    extensiones, tamanos, estructura, mensajes de validacion y pantallas
    redactadas si son necesarias.
11. Restaurar snapshot o destruir la VM.

## Evidencia permitida

- Matriz de pasos y modulos usados.
- Campos/codigos F22/DDJJ observados como identificadores tecnicos.
- Estructura de archivos generados sin contenido real.
- Mensajes de validacion redactados.
- Capturas solo si no contienen RUT, folio, clave, licencia, certificado,
  correo, ruta sensible ni dato real.

## Evidencia prohibida

- Binarios EDIG.
- MDB originales o modificados.
- Archivos de upload con datos reales.
- Licencias, llaves, certificados, claves SII o tokens.
- RUTs reales, folios reales, declaraciones reales, correos o pantallas con
  informacion tributaria identificable.

## Resultado esperado

El resultado debe alimentar `docs/product/RENTA_ANUAL_EDIG_AT2026_MAPPING.md`
con diferencias observadas entre:

- contabilidad/balance;
- registros tributarios intermedios;
- F22/DDJJ;
- validaciones;
- export/upload;
- estados y evidencia de revision.

Si el flujo requiere internet, certificado, licencia productiva o clave real, se
detiene y se registra como bloqueo externo. No se abre el gate SII.
