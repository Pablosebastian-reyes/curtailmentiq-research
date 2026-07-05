# Reglas de data-raw/

1. Aquí van los archivos ORIGINALES del CEN tal como se descargaron, INCLUYENDO los que contienen erratas. Son la evidencia del data paper.
2. Inmutables: nunca editar, nunca renombrar, nunca borrar.
3. Al agregar archivos, correr desde la raíz del repo:
   `python scripts/make_checksums.py`
   Esto registra SHA-256 + fecha en CHECKSUMS.sha256. Commitear ese archivo.
4. Los binarios pesados están fuera de git (ver .gitignore): mantener respaldo espejo en almacenamiento propio (disco + nube). El checksum permite verificar integridad de cualquier copia.
