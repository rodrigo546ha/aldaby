# ADR-0026: PDF del plan con todas sus fuentes

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.8

## Contexto
F6.8 pide exportar el plan completo (ADR-0025) a PDF con todas las fuentes citadas. PLAN_DISENO
deja abierta la elección del motor: imprimir desde la web o generar el PDF en Python.

## Decisión
- **WeasyPrint en la API** (BSD, 70.0). `reports/` escribe el plan en HTML con su CSS y
  WeasyPrint lo convierte. Solo `reports/` importa `weasyprint`. Necesita pango y cairo:
  - **En el Mac:** de Homebrew, con `DYLD_FALLBACK_LIBRARY_PATH` que el Makefile pone delante de
    `make api` y `make test` (`PDF_LIBS`).
  - **En el contenedor de AWS (G8):** los paquetes de pango del sistema.
- **Contenido:** lo calculado y nada más. Cabecera con la oferta y si encaja, una sección por
  apartado del plan con cada cifra, su fórmula y sus notas, los cambios con las normas
  pendientes, el tipo de alquiler y la gestión, los argumentos para no comprar del programa, la
  hoja de ruta con el enlace de cada paso, los avisos y un anexo de fuentes. **La explicación y
  los argumentos del asesor no van:** el PDF sale al momento y el mismo plan da el mismo PDF.
- **Fuentes con notas numeradas.** Cada cifra lleva los números de sus fuentes, y el anexo final
  lista cada fuente una vez:
  - **norma:** su enlace oficial, la vigencia y si está verificada;
  - **parámetro:** de dónde sale y su enlace;
  - **datos:** el nombre, el enlace, la licencia y la fecha de descarga de `sources`;
  - **modelo, supuesto o dato del usuario:** qué es, en una frase.
  Lo provisional se marca.
- **Formato de las cifras en el servidor, sin `float`** (`reports/format.py`): euros con dos
  decimales y puntos de miles, porcentajes desde el tanto por uno, en español. Las etiquetas de
  las cifras van en `reports/labels.py`, como las de la web.
- **No se guarda.** `GET /plans/offers/{id}/pdf` lo genera al pedirlo, con
  `Cache-Control: no-store`: lleva datos personales (capacidad, ahorro) y así no hay nada que
  custodiar. Si hace falta un histórico, se decidirá en la beta.
- **Web:** un enlace «Descargar PDF» en `/plan`.

## Opciones consideradas
- **Imprimir desde el navegador:** sin dependencias, pero el resultado depende del navegador y la
  API no puede generar el PDF para enviarlo (profesionales, F7).
- **fpdf2:** Python puro (LGPL), sin bibliotecas de sistema, pero la maquetación se escribe a mano
  y el anexo de fuentes con enlaces cuesta mucho más.
- **Chromium sin interfaz:** la dependencia más pesada de todas.

## Consecuencias
- Una dependencia con bibliotecas de sistema: el contenedor de la beta tiene que instalarlas.
- Las etiquetas de las cifras están dos veces (web y PDF): una clave nueva va a los dos sitios.
