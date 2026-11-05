#!/usr/bin/env bash
# Reproduce de punta a punta la segunda revision (SEGAN-D-26-03850R1 -> R2).
# Se corre desde curtailmentiq-research/revision2/ (o desde una carpeta hermana
# del repositorio). Lee el codigo de flagship/ y los datos de release/v1.0. Tiempo aproximado en un portatil de
# 8 nucleos: 1.5 a 2 horas, dominado por la simulacion y la sensibilidad.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}   # entorno: environment.yml del repositorio
export PYTHONDONTWRITEBYTECODE=1

$PY scripts/r2_01_predictivas.py      # 9 modelos base, verificados contra la R1
$PY scripts/r2_02_metodos.py          # todas las capas sobre los 9 modelos
$PY scripts/r2_03_diagnostico.py &    # oraculo, inferencia, fuera de muestra
$PY scripts/r2_04_operacional.py &    # ponderaciones, dias altos, costo
$PY scripts/r2_05_simulacion.py &     # simulacion controlada
$PY scripts/r2_06_sensibilidad.py &   # apendice E
wait
$PY scripts/r2_13_tiempos.py          # tiempos limpios (correr con la maquina en reposo)
$PY scripts/r2_08_tablas.py           # ablaciones y todas las tablas
$PY scripts/r2_09_figuras.py          # figuras nuevas
$PY scripts/r2_07_cifras.py           # cifras del texto
$PY scripts/r2_12_verificar.py        # afirmaciones cualitativas contra resultados
$PY scripts/r2_10_ensamblar.py --empaquetar   # compila, aplana y empaqueta
$PY scripts/r2_11_marcado.py          # version marcada R1 -> R2
