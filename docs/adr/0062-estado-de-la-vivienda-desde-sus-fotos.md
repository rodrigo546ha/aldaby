# ADR-0062: Saber si la vivienda necesita reforma mirando sus fotos

- **Estado:** propuesta. Para aceptarla faltan la consulta legal sobre los derechos de las fotos
  (F0.6), el umbral de calidad y las fotos del juego de evaluación.
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («Sí, prepáralo», sobre el ADR y el juego de fotos etiquetadas)

## Contexto

Desde el commit 888d63c, el plan avisa cuando el texto del anuncio dice «a reformar» y pide el
coste de la reforma. Muchos anuncios no dicen nada del estado, pero sus fotos sí lo enseñan: una
cocina de los setenta, un baño sin actualizar, humedades.

Lo que hay hoy:

| Canal | Fotos | Interior |
|---|---|---|
| Subastas del BOE y del Portal | Fachada del Catastro y ortofoto del PNOA (ADR-0054) | No |
| Anuncios pegados | La imagen principal que declara la página (`og:image`), que ya se descarga para la tarjeta | A veces |
| Feeds de agencias (Kyero) | El XML trae la lista; ADR-0038 no guarda sus URL hasta F0.6 | Sí |

Ningún modelo cargado ve imágenes: en el Mac solo hay modelos de texto (ADR-0014).

## Decisión propuesta

1. **Qué dice el modelo: nada con cifras.** Para cada inmueble, a partir de sus fotos:
   - un veredicto cerrado: `necesita_reforma`, `no_necesita` o `no_se_sabe`, que es la respuesta
     obligada si las fotos no enseñan el interior;
   - una lista de señales de un vocabulario cerrado (`evaluations/photos.py`, `SIGNS`), cada una
     con el número de la foto en la que se ve.

   Nunca da un coste, un descuento ni un porcentaje (regla de oro 1).
2. **Comprobación, como la cita literal de la extracción (ADR-0013).** Se rechaza la respuesta si:
   - cita una foto que no existe;
   - da una señal fuera del vocabulario;
   - dice `necesita_reforma` sin ninguna señal de reforma;
   - dice `no_necesita` con alguna.
3. **El usuario confirma.** El plan enseña la foto citada junto a cada señal y pregunta si hay que
   reformar. Solo una confirmación activa el flujo que ya existe: el aviso y el campo del coste de
   la reforma, que se suma a la compra. La valoración no cambia.
4. **Modelo:**
   - **Interfaz:** un método de visión en `agent/llm.py` con la misma salida estructurada. Las
     imágenes van como partes `image_url` de la API compatible con OpenAI, que entienden Ollama con
     modelos de visión y los proveedores de API.
   - **Elección:** el modelo se elige con el juego de evaluación, junto a la comparación de
     proveedores pendiente (`docs/research/f7-proveedor-llm.md`).
5. **De dónde salen las fotos, en este orden, y todas solo cuando F0.6 lo permita:**
   - las de los feeds de agencias, con la cesión expresa en el alta del feed (ADR-0038);
   - la imagen principal del anuncio pegado;
   - la fachada del Catastro, que sirve para el edificio y no para el piso.

   No se piden galerías de portales: sería scraping (regla de oro 3).
6. **Sin guardar:** las fotos se analizan en memoria, como las de las tarjetas (ADR-0054). Se
   guardan el veredicto, las señales y el número de foto. Al modelo no se le pregunta por personas
   ni objetos personales.
7. **Puerta de calidad:**
   - el análisis no se enseña hasta que pase un juego etiquetado a mano (`data/evaluation/fotos.yaml`);
   - las fotos del juego van en `tests/fixtures/private/fotos/`, fuera de git, y en el repositorio
     solo las etiquetas;
   - métricas: acierto del veredicto, precisión y exhaustividad de `necesita_reforma`, cuántas veces
     dice `no_se_sabe` y si las señales citan la foto correcta (`evaluations/photos.py`);
   - el umbral para enseñarlo lo fija Rodrigo con la primera medición.

## Opciones consideradas

- **Descontar el valor según las fotos:** sería una cifra sin fuente que sale de un modelo, contra
  las reglas de oro 1 y 4. Descartado, como el descuento por estado del texto.
- **Pedir la galería completa del portal:** más fotos, pero es scraping y los derechos son del
  anunciante. Descartado.
- **Solo la fachada del Catastro:** está en todas las ofertas ubicadas, pero no enseña el piso.
  Queda como señal del edificio.

## Consecuencias

- Hasta F0.6 no hay fotos que analizar en producción. El juego de evaluación se puede preparar
  antes, con fotos sobre las que haya derechos: propias, de agencias del piloto que lo cedan por
  escrito o con licencia abierta.
- Si el modelo no pasa el umbral, el plan sigue como hoy: el estado sale solo del texto.
