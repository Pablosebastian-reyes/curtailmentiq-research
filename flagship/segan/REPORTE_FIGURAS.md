# Reporte de figuras SEGAN

Generadas por `flagship/generar_figuras_paper.py` con el venv de
`curtailmentiq-model`. Salidas en `flagship/segan/figuras/` (PDF vectorial para
LaTeX + PNG 300 dpi para revisar). Textos en ingles; comentarios del script en
espanol.

## Estilo comun (definido una sola vez en el script)

- PDF vectorial + PNG 300 dpi. Fuentes embebidas como TrueType (`pdf.fonttype=42`).
- Ancho columna simple 3.5 in, columna doble 7.2 in.
- Fuente serif (Times New Roman, fallback DejaVu Serif) 7.5 a 8.5 pt; math en STIX
  para los simbolos gamma.
- Sin titulo dentro de la figura (va el caption en LaTeX); sin spines superior ni
  derecho; sin grillas pesadas.
- Paleta sobria validada con el validador de la skill dataviz (modo light,
  `--pairs all`): peor par CVD dE 9.1 (sobre el objetivo 8), peor par de vision
  normal dE 16.3 (sobre el piso 15). El unico WARN es contraste de solar y
  run-of-river contra el fondo blanco; se cubre con la "relief rule" (marcador
  propio por tecnologia + leyenda con etiqueta), asi la identidad nunca depende
  solo del color.
- Codificacion secundaria siempre presente: cada tecnologia lleva marcador propio
  (Solar circulo, Wind triangulo, Run-of-river cuadrado, Reservoir rombo); cada
  metodo conformal lleva estilo de linea y hatch propios.

## Fuentes de datos por figura

| Figura | Ancho | Fuente de datos |
|---|---|---|
| fig1_plants_map | simple | `release/v1.0/plants.parquet`, `plants_metadata.parquet` (lat/lon), `curtailment_daily.parquet` (acumulado por central). Contorno de Chile: `scripts/chile_boundary.geojson` (Natural Earth 1:50m, dominio publico). |
| fig2_distribution | simple | `release/v1.0/curtailment_daily.parquet` (fraccion de ceros por tecnologia; magnitudes positivas). |
| fig3_rolling_coverage | doble | Recomputa las 4 series conformal desde `flagship/predicciones/pred_hurdle.csv` reutilizando `conformal_v3_real.py` + `conformal_metodos.py`, corrida CON embargo de 7 dias. |
| fig4_coverage_width | doble | `flagship/conformal_v3_tabla.csv` (corrida oficial con embargo). |

## Contenido y valores clave (tomados de los datos, no inventados)

- **Fig 1.** 300 centrales, area del marcador proporcional al curtailment
  acumulado 2022-2026. Solar concentrada en el norte (Atacama), hidro en el sur;
  patron espacial coherente con el sistema.
- **Fig 2.** Justifica el modelo hurdle. Panel superior, fraccion de dias en cero
  por tecnologia: Solar 0.27, Wind 0.28, Run-of-river 0.78, Reservoir 0.95
  (global 0.498, consistente con el "49.8%" del data paper). Panel inferior, las
  magnitudes positivas son aproximadamente lognormales (campana en escala log) con
  cola pesada: P50 = 43, P90 = 356, P99 = 1,076 MWh.
- **Fig 3.** Cobertura rodante 90d. El static split se mantiene alto (sobrecubre)
  y los metodos adaptativos siguen mas de cerca el 90% nominal. Se ve la banda de
  la rampa BESS (oct a dic 2024) y la caida comun de todos los metodos alrededor
  de mayo a julio 2025 (evento de segundo orden documentado en `DECISIONS.md`).
- **Fig 4.** Trade-off cobertura vs sharpness por periodo. En la rampa el static
  split llega a 95.3% con ancho 1203 MWh; transporte+ACI baja a 90.9% con 806 MWh
  (33% mas angosto) manteniendo la cobertura cerca del nominal. Barras de error =
  se de cobertura clusterizado por fecha.

## Decisiones visuales (para revisar y vetar si corresponde)

1. **Sin geopandas ni cartopy en el venv**, la Fig 1 usa el contorno de Chile del
   geojson de Natural Earth ya presente en el repo y ubica las centrales por
   lon/lat con aspecto corregido por latitud (`1/cos(30 deg)`). Chile queda como
   su franja N-S caracteristica.
2. **Leyendas de la Fig 1 en el Pacifico (oeste), dentro de los ejes.** Para un
   mapa de columna simple tan alargado, el oceano al oeste esta vacio de datos
   (todas las centrales caen en la franja este), asi que ubicar ahi las dos
   leyendas evita encoger el mapa y no solapa ninguna central. Si prefieres las
   leyendas estrictamente fuera de los ejes (debajo del mapa), es un cambio de dos
   lineas en `figura_1` (mover los `bbox_to_anchor`); lo dejo asi porque en 3.5 in
   una leyenda externa a la derecha adelgaza demasiado el mapa.
3. **Fig 3 reproduce exactamente la corrida oficial.** El script recomputa las
   series respetando el mismo orden de consumo del RNG que `main()` de
   `conformal_v3_real.py` (score PIT randomizado del atomo, luego transporte g02 y
   g05), y **se autochequea** contra `conformal_v3_tabla.csv`: aborta si alguna
   cobertura o ancho agregado difiere (tolerancia 0.15 pp y 1 MWh). El check paso.
4. **Fig 4, asterisco en el panel de ancho.** El ancho medio se calcula solo sobre
   intervalos finitos; las barras con una fraccion no trivial (>= 1%) de
   intervalos infinitos (ACI y transporte con gamma=0.05 en 2025-H1 y 2025-H2)
   llevan un asterisco. Conviene explicarlo en el caption de LaTeX.
5. **Metodos mostrados en Fig 3 y Fig 4.** Se eligieron los 4 titulares (static,
   ventana 60d, ACI g05, transporte+ACI g05) para legibilidad; las variantes g02
   estan en la tabla y pueden agregarse si el revisor las pide.

## Reproducir

```
cd curtailmentiq-research
../curtailmentiq-model/venv/bin/python flagship/generar_figuras_paper.py
```
