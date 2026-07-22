# 5. Results

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 5).

## 5.1 Benchmark sintetico
Cierre de la tabla comparativa sobre el panel sintetico (no citable como evidencia): el pool deslizante resuelve el colapso del pool fijo; la ventana y el ACI recuperan sharpness bajo la rampa; la banda del transporte es inerte porque el ancho de la transicion no es ruido de muestreo.
- Material: `../conformal_v2_cierre_salida.txt`, `../conformal_v2_cierre_tabla.csv`, `../conformal_v3_hallazgos.txt` (parte A), `../conformal_v2_cobertura_rodante.png`.

## 5.2 Datos reales
La maquinaria PIT funciona de extremo a extremo; la sobrecobertura severa del sintetico no aparece porque el modelo base absorbe el quiebre; la adaptatividad paga sobre todo en la rampa (transporte mas ACI baja el ancho de 1203 a 732 MWh con 90.7% de cobertura) y es ambigua fuera de ella; el techo de sharpness lo fija sigma = 1.70; las diferencias de 1 a 3 puntos estan dentro del error estandar clusterizado. Sensibilidad al embargo dentro del error estandar y sin sesgo direccional.
- Material: `../RESULTADOS_REALES.md` (secciones 1 a 5), `../conformal_v3_tabla.csv`, `../conformal_v3_salida.txt`, `../conformal_v3_cobertura_rodante.png`, `../conformal_v3_hallazgos.txt` (partes B a F).

## 5.3 Resultado negativo: weighted conformal por punto
El weighted conformal por punto con score PIT entrega intervalos infinitos en una fraccion alta de los casos (ESS de calibracion colapsado); el fallo es por falta de solapamiento en las X y es robusto entre score aditivo y PIT.
- Material: `../conformal_v2_cierre_salida.txt` (parte A.c), `../conformal_v3_hallazgos.txt` (parte A.c y B.1), `../AUDIT_METODOLOGICO.md` (punto 4).

## 5.4 Resultado negativo secundario: sigma(x) heterocedastico
El modelo base heterocedastico mejora solo marginalmente los scores propios, no mejora la calibracion global e introduce sub-cobertura en las centrales grandes; el diagnostico condicional muestra que el quiebre es un shift de ubicacion, no de dispersion.
- Material: `../RESULTADOS_REALES.md` (seccion 6), `../entrenar_hurdle_hetero_salida.txt`, `../hurdle_hetero_pit.png`, `../predicciones/pred_hurdle_hetero.csv`, `../../DECISIONS.md` (2026-07-20, sigma(x) descartado).
