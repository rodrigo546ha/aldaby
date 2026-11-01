# Extracción de lotes del BOE: por qué se quedaban sin ubicar y qué mejoró (ADR-0033)

Fecha: 2026-11-01 · Modelo: qwen3-14b-hf (Ollama local, sin GPU)

## Punto de partida
De 62 lotes extraídos de la sección V, 32 no tenían ni dirección ni referencia catastral. En
todos, la comprobación de citas había rechazado lo que propuso el modelo:

| Causa | Lotes | Ejemplo |
| --- | --- | --- |
| Sin tramo: la etiqueta no es una cita literal | 22 | «El texto original menciona 'Finca 1'…»; «Lote 2» por «Lote nº 2.-» |
| La dirección no está tal cual en la cita | 9 | «Plaza Cuartel 6, Cacín» de «en CACÍN (Granada), Plaza Cuartel, 6» |
| … y además la referencia, con espacios o barras | 5 de esos 9 | «21026A0 0400061 0000», «2006983/9728140/0439/9E» |
| La cita es una frase del modelo | 1 | «El documento menciona la ubicación de…» |

## Medición
El banco de F6.9 (`data/evaluation/`) se amplió con seis anuncios reales de la sección V
(32776, 32279, 35361, 35250, 31752 y 33450): 22 anuncios, 19 lotes del BOE, 274 campos con valor
esperado.

| | Antes | Después |
| --- | --- | --- |
| Campos correctos | 148 / 274 | 207 / 274 |
| Falta | 104 | 42 |
| Distinto | 6 | 5 |
| Sobra | 9 | 10 |
| Lotes de más / de menos | 1 / 6 | 0 / 0 |

Fallos por anuncio del BOE (antes → después): Granada 33 → 2, Badajoz 20 → 3, cuarteles 12 → 3,
Huelva 4 → 3, Donostia 4 → 3, Alcalá 4 → 2, Marín 3 → 4. Los anuncios de portal sintéticos no
cambian (las reglas nuevas solo afectan a los lotes).

La pasada «después» se hizo en dos veces: el anuncio de Granada (cinco lotes) superó los 600 s de
espera del cliente y se repitió solo, con 1.500 s (tardó 908 s). Se sumaron las dos pasadas, y dos
lecturas válidas que el banco no admitía («c/ General Prim, 34, Trigueros», «polígono ciento
cuatro, parcela siete») se añadieron como respuestas aceptadas.

## Lo que queda
- `property_type`: el modelo pone «local» a casi todo o su cita no está en el tramo.
- Referencias dentro de tablas aplanadas (Marín: «… PONTEVEDRA 2 5441307NG2954S0001QR»).
- Tiempo: un anuncio de cinco lotes tarda unos 15 minutos sin GPU. `LLM_TIMEOUT_S` pasa a 1800 en
  `.env.example`.

## Nueva extracción de los 16 anuncios (2026-11-01)
Los 16 anuncios con lotes sin ubicar se volvieron a extraer con las reglas de ADR-0033. Antes
estaban ubicados 26 de 62 lotes; después, 33 de 59 (cinco retirados). Lo que queda sin ubicar:

| Causa | Lotes | Anuncios |
| --- | --- | --- |
| Anuncio largo: el modelo solo ve el final o su salida no es válida | 15 | 32556, 32775, 32777, 31848 |
| CartoCiudad no encuentra un paraje o una partida rural | 6 | 32279, 32776, 33450, 33521, 35361 (2) |
| Rechazo correcto: la referencia es de otro municipio o CartoCiudad lo sitúa en otro | 2 | 33611 (Requena), 35111 (Segorbe → Xixona) |
| Cita del modelo que no está en el documento | 2 | 32776#1, 34188 (Salamanca) |
| Referencia de Gipuzkoa con una forma que no se conoce | 1 | 33449 (`82950960147121N`) |

Los anuncios largos eran el hueco grande: seis anuncios con unos 175 lotes en el texto y 15
extraídos. Ver ADR-0034.

## Anuncios largos por partes (2026-11-01)
Con ADR-0034, los seis anuncios largos se volvieron a extraer por partes. De los 16 anuncios de
arriba, están ubicados 126 de 152 lotes (antes, 33 de 59). En toda la base, 171 de 198 lotes.

| Anuncio | Lotes | Ubicados | Tiempo |
| --- | --- | --- | --- |
| 34259 | 20 | 20 | 18 min |
| 31747 | 9 | 8 | 12 min |
| 31848 (Asturias) | 17 | 12 | 17 min |
| 32777 (Lugo) | 48 | 45 | 47 min |
| 32556 (Valencia) | 51 | 48 | 55 min |
| 32775 (El Frasno) | 9 | 5 | 43 min |

Lo que se ha visto:

- **El Frasno salió como 67 lotes**: el modelo sacó cada finca («9.1», «9.2»…) como un lote,
  pese a las instrucciones, y desalineó algunas (la «9.1» con los datos de la 9.2). Ahora se
  juntan en su lote antes de comprobar (ADR-0034, decisión 5). Quedan sin ubicar los lotes 1, 2, 6
  y 7: el modelo no dio la referencia de ninguna de sus fincas, y la dirección nombra varias
  parcelas, que el paso de polígono y parcela no acepta a propósito (ADR-0031).
- **Asturias (31848)**: el texto tiene 34 líneas «Lote…», 17 lotes y 17 filas de la tabla de
  precios («Lote 1 2ª subasta…»). Las filas cerraban el tramo del lote antes de su precio, y el
  modelo sacó los lotes de varias parcelas una vez por parcela, con la misma etiqueta.
- **31747 (Aldeadávila de la Ribera)**: 13 lotes; el modelo se saltó del 8 al 11 en su parte.

## Asturias y Aldeadávila (2026-11-01)
Con las decisiones 6 a 8 de ADR-0034 (la fila de precios no empieza un lote, los elementos del
mismo encabezado se juntan, el lote que el modelo se salta se pide otra vez), más dos arreglos
pequeños, los dos anuncios se volvieron a extraer:

| Anuncio | Lotes | Ubicados | Con precio | Tiempo |
| --- | --- | --- | --- | --- |
| 31848 (Asturias) | 17 (antes 17, 4 sin etiqueta) | 17 (antes 12) | 11 (antes 0) | 19 min |
| 31747 (Aldeadávila) | 13 (antes 9) | 13 (antes 8) | 12 | 15 min |

- «Cangas de Narcea» en el anuncio es «CANGAS DEL NARCEA» en el Catastro: al comparar
  municipios, «del» cuenta como «de».
- En el lote 12 de 31747 el modelo juntó las referencias de sus fincas en una cita de varias
  líneas que no es seguida en el documento: vale la primera, con su línea.
- En 31848 faltan los precios de los lotes 9 a 14: el modelo no los da (no es la comprobación).

En toda la base, 181 de 202 lotes ubicados.

## Lotes sin ubicar por fallo nuestro (2026-11-02)
De los 21 lotes sin ubicar, 14 eran fallos nuestros (ADR-0035). Recomprobados sin LLM, quedan
7 de 202:

| Lote | Causa | Qué haría falta |
| --- | --- | --- |
| 32775#1, #2, #7 (El Frasno) | El modelo no dio la referencia de ninguna finca; la dirección nombra varias parcelas | Pedir al modelo la referencia de la primera finca, o ubicar por la primera parcela nombrada |
| 32775#6 (El Frasno) | El modelo no dio nada que lo ubique | Lo mismo |
| 32777#17 (Mondoñedo) | Paraje rural sin referencia; CartoCiudad no lo conoce | Nomenclátor geográfico (IGN), si sus condiciones lo permiten |
| 32777#35 (A Pontenova) | El Catastro dice que la referencia del BOE no existe | Nada: avisar en el lote |
| 33611#1 (Requena) | La parcela es de otro municipio que el que dice el anuncio | Nada: rechazo correcto |

