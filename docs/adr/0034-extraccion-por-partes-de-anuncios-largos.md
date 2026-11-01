# ADR-0034: Extracción por partes de los anuncios largos

**Estado:** Aceptada · **Fecha:** 2026-11-01 · **Decide:** Rodrigo (pide cerrar los huecos de la
extracción de lotes tras ADR-0033)

## Contexto
Tras volver a extraer los 16 anuncios de ADR-0033, quedaban seis anuncios largos con muy pocos
lotes:

| Anuncio | Caracteres | Lotes en el texto | Lotes extraídos |
| --- | --- | --- | --- |
| BOE-B-2026-32775 (El Frasno) | 80.107 | 9 (de 11 fincas o más) | 2 (los lotes 8 y 9) |
| BOE-B-2026-32556 (Valencia) | 62.402 | 51 | 3 (los lotes 49 a 51) |
| BOE-B-2026-32777 (Lugo) | 40.875 | 48 | 0: salida no válida |
| BOE-B-2026-31848 (Asturias) | 36.415 | 34 | 0: salida no válida |
| BOE-B-2026-31747 | 21.411 | 13 | 0 |
| BOE-B-2026-34259 | 12.798 | 20 | sin extraer |

El modelo local (qwen3:14b en Ollama) tiene una ventana de 16.384 tokens. Los anuncios del BOE
van a 2,4 caracteres por token (medido con 8.000 caracteres de 32556: 3.290 tokens): 62.402
caracteres son unos 25.700 tokens. Ollama descarta el principio de lo que no cabe, así que el
modelo solo ve el final, y por eso devuelve los últimos lotes. Si el texto casi llena la ventana,
la respuesta se queda a medias y no es JSON válido. El fallo es silencioso: en 32775 la extracción
nueva retiró cuatro lotes (ADR-0033) que el modelo ya no había visto.

Hay además dos fallos de la comprobación:

- **Fincas dentro de un lote.** En 32775, el «LOTE Nº 1» tiene once fincas («1.1», «1.2»…). Los
  encabezados de ADR-0033 cortaban el tramo del lote en «1.1», y su referencia catastral se
  quedaba fuera.
- **Citas envueltas en una frase del modelo.** El modelo escribía, por ejemplo, «The text states
  'municipio de UTIEL'». La cita literal está entre las comillas, pero la frase entera no está en
  el documento.

## Decisión
1. **Partes con lotes enteros.** Un anuncio de más de 12.000 caracteres que tiene encabezados
   «Lote…» se manda al modelo por partes. Cada parte lleva el preámbulo (título y lo que va antes
   del primer lote) y como mucho seis lotes enteros. Un lote no se corta. Ninguna parte pasa de
   20.000 caracteres, el mismo límite que `agent/documents.py`: lo que se queda fuera es el final
   del último lote, que son las condiciones comunes del pliego. Cada parte se comprueba contra su
   propio texto, y los lotes se juntan en orden.
2. **Lo propuesto, por partes.** `extracted.proposed` guarda la respuesta de cada parte y el
   tamaño con el que se partió. `recheck` vuelve a partir el anuncio igual y lo comprueba sin el
   LLM.
3. **Los encabezados «Lote…» mandan.** Si un documento los tiene, los demás encabezados («1.1»,
   «Finca 1:») son fincas de un lote y no cierran su tramo. Las instrucciones le dicen al modelo
   que un lote de varias fincas es un solo elemento, con la ubicación de su primera finca.
4. **Cita entre comillas.** Si una cita no está en el documento, vale el fragmento más largo
   entre comillas que sí está. El valor se sigue comprobando contra ese fragmento, y lo propuesto
   se guarda tal como llegó.

Con todo esto, cada valor sigue saliendo de un texto literal del anuncio, dentro del tramo de su
lote.

## Opciones consideradas
- **Ampliar la ventana del modelo a 40.960 tokens.** Con 40.960, Ollama ya no cabe entero en la
  GPU de este Mac (14 % en CPU) y es mucho más lento. Además, la respuesta de 51 lotes (unos 700
  tokens cada uno) tampoco cabría.
- **Una llamada por lote.** 51 llamadas para un anuncio, todas con el mismo preámbulo. Agrupar
  hasta seis lotes reparte mejor el tiempo, y el tamaño se puede ajustar (`PART_CHARS`,
  `PART_LOTS`).
- **Cortar el documento sin mirar los lotes.** Un lote partido en dos daría citas fuera de su
  tramo.

## Consecuencias
- Los seis anuncios se vuelven a extraer. Los lotes retirados en 32775 vuelven si la extracción
  nueva los encuentra (`refresh_lot` actualiza también los retirados).
- Un anuncio largo tarda más en total (32556 son 10 llamadas), pero cada llamada es más corta y
  cabe en la ventana.
- Comprobado sin LLM sobre lo que el modelo ya había propuesto: los lotes con dirección o
  referencia pasan de 25 a 30 (32556: de 0 a 3; 32775: de 0 a 2).
