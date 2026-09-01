# build/ — carpeta de compilacion, autocontenida

Contiene los dos documentos compilados y todo lo que necesitan: las ocho figuras
en PDF y los diez cuerpos de tabla generados desde `resultados/`. Se puede subir
tal cual a Overleaf, o compilar en el sitio con:

```
pdflatex SEGAN_paper_FINAL.tex      # tres pasadas, por las referencias cruzadas
pdflatex response_to_reviewers.tex  # dos pasadas
```

Los .tex y los .pdf de figura son COPIAS. Las fuentes vivas son
`flagship/segan/*.tex`, `flagship/segan/figuras/*.pdf` y
`resultados/tablas_tex/*.tex`. Para refrescar la carpeta:

```
cp flagship/segan/SEGAN_paper_FINAL.tex flagship/segan/response_to_reviewers.tex build/
cp flagship/segan/figuras/*.pdf resultados/tablas_tex/*.tex resultados/fase1/hiperparametros.tex build/
```

Los auxiliares de LaTeX (.aux, .log, .out, .toc, .spl) no se versionan.
