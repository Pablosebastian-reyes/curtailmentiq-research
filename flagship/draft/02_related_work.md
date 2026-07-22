# 2. Related work

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 2):
- Conformal prediction: split conformal y CQR (Romano, Patterson y Candes 2019).
- Score distribucional o PIT (Chernozhukov, Wuthrich y Zhu 2021).
- Cambio de distribucion: weighted conformal bajo covariate shift (Tibshirani et al. 2019); conformal mas alla de la intercambiabilidad y pesos de recencia (Barber, Candes, Ramdas y Tibshirani 2023).
- Conformal adaptativo online: ACI (Gibbs y Candes 2021), DtACI (2022), conformal PID (Angelopoulos, Candes y Tibshirani 2023).
- Descomposicion de shifts: Ai y Ren (2024); alternativa DRO (Cauchois, Gupta, Ali y Duchi 2024); variante series de tiempo (Xu y Xie, EnbPI).
- Transporte optimo y conformal: linea de center-outward ranks (deslinde: usan OT para construir el score, aqui se usa para adaptarlo entre regimenes).

## Material del repo que alimenta esta seccion

- Triage de referencias y deslinde de la contribucion OT: `../AUDIT_METODOLOGICO.md` (punto 5, ultimo bloque) y `../HANDOFF_KERVEN.md`.
- Ubicacion de cada metodo citado dentro del pipeline propio: `../conformal_metodos.py` y `../INDICE_PAPER.md` (seccion 4).
