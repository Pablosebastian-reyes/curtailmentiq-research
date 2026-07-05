# etl/

Scripts de descarga y procesamiento. Convenciones:
- `01_download_*.py`: descarga desde el CEN (registrar URL y fecha en el log del script).
- `02_clean_*.py`: limpieza y corrección de erratas (cada regla referencia su fila en ERRATA_LOG.md).
- `03_build_*.py`: construcción de tablas analíticas / carga a Neon.
Todo script debe correr de punta a punta sin intervención manual.
