# 1. Introduction

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 1):
- Problema aplicado: prediccion de vertimiento por central en el sistema electrico chileno con cuantificacion de incertidumbre util para operacion.
- El giro metodologico: el pronostico de punto esta agotado (un baseline estacional trivial gana en MAE), asi que el valor esta en la capa de incertidumbre.
- El desafio central: el quiebre BESS es una rampa de 15 meses, no un escalon, y obsoleta toda calibracion estatica.
- Contribuciones: (i) diagnostico del quiebre como rampa y no como covariate shift; (ii) resultado negativo del weighted conformal por punto; (iii) resultado positivo de adaptacion por recencia y transporte de scores mas ACI; (iv) linea teorica de transporte del score entre regimenes.

## Material del repo que alimenta esta seccion

- Tabla de MAE de baselines (naive estacional gana): `../predicciones/README.md`, seccion Reporte descriptivo.
- Diagnostico del quiebre como rampa: `../AUDIT_METODOLOGICO.md` (punto 5) y `../RESULTADOS_REALES.md` (seccion 2).
- Enunciado de las cuatro contribuciones: `../INDICE_PAPER.md` (seccion 1) y `../conformal_v3_hallazgos.txt` (partes A a F).
- Contexto de arquitectura de publicacion (data paper primero, flagship despues): `../../DECISIONS.md`, entrada 2026-07-03.
