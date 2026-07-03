# Log de erratas — archivos oficiales del CEN

Registro formal de las erratas detectadas en los archivos públicos de curtailment del Coordinador Eléctrico Nacional, con su regla determinística de detección y corrección. Este log es la base de la contribución del data paper.

**Instrucciones:** una fila por errata. El archivo original con la errata debe estar preservado en `data-raw/` con su checksum. Completar TODAS las columnas.

| # | Archivo original (data-raw/) | Fecha del archivo | Fecha de detección | Campo/columna afectada | Descripción de la errata | Valor(es) errado(s) | Regla determinística de detección | Corrección aplicada | Evidencia de contraste |
|---|---|---|---|---|---|---|---|---|---|
| 1 | *(completar)* | | | | | | | | |
| 2 | *(completar)* | | | | | | | | |
| 3 | *(completar)* | | | | | | | | |
| 4 | *(completar)* | | | | | | | | |
| 5 | *(completar)* | | | | | | | | |
| 6 | *(completar)* | | | | | | | | |

## Notas

- "Regla determinística" = condición verificable por código que detecta la errata (ej: "suma horaria difiere del total diario reportado en más de X%").
- "Evidencia de contraste" = fuente independiente que confirma que el valor corregido es el correcto (otro archivo CEN, informe mensual, reconstrucción aritmética).
- Estas reglas se implementan en `etl/` y se describen en la sección Methods del data paper.
