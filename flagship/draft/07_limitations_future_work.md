# 7. Limitations and future work

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 7):
- Modelo base heterocedastico sigma(x): probado y descartado como modelo base por sub-cobertura en centrales grandes; el shift es de ubicacion, no de dispersion. Queda como resultado negativo, no como pendiente.
- Deteccion de change-point: la caida de cobertura comun a todos los metodos alrededor de mayo a julio de 2025 no es anticipada por ningun metodo; se reporta como limitacion caracterizada con un diagnostico corto del episodio.
- Validez exacta de muestra finita del transporte: se pierde por ser el mapa dato-dependiente; se recupera via cota TV o via control online.
- Alcance del panel sintetico: banco de pruebas, no evidencia empirica.

## Material del repo que alimenta esta seccion

- sigma(x) como resultado negativo: `../RESULTADOS_REALES.md` (seccion 6), `../../DECISIONS.md` (2026-07-20, sigma(x) descartado), `../ESPECIFICACION_SIGMA_X.md`.
- Episodio de mayo a julio de 2025: `../conformal_v3_hallazgos.txt` (parte C.5), `../conformal_v3_cobertura_rodante.png`, `../RESULTADOS_REALES.md` (observacion estructural).
- Validez del transporte: `../AUDIT_METODOLOGICO.md` (punto 5), `../HANDOFF_KERVEN.md`.
- Decisiones de alcance (que entra y que es futuro): `../../DECISIONS.md` (2026-07-20, cierre de alcance).
