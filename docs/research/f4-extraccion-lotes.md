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
  `.env.example`; con anuncios más largos, la opción es una llamada por lote (ADR-0033).
