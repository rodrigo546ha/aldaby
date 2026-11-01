# ADR-0035: Nombres de lugar en las lenguas oficiales y consultas de ubicación

**Estado:** Aceptada · **Fecha:** 2026-11-02 · **Decide:** Rodrigo («hay que aceptar las
diferencias de nombre entre idiomas oficiales»; arreglar los lotes sin ubicar que son fallo
nuestro)

## Contexto
Tras ADR-0034 quedaban 21 de 202 lotes sin ubicar. Catorce eran fallos nuestros, no de las
fuentes:

| Fallo | Lotes | Ejemplo |
| --- | --- | --- |
| Varias referencias en un valor, o texto delante | 6 | «06029A006000170000GO y 06029A006000180000GK»; «Plaza de Garaje nº 9: 7531501TL7473S0009GB» |
| Consulta a CartoCiudad con provincia, «nº» o coma ante el número | 4 | «Paseo de la Marina nº 5, Garrucha (Almería), Garrucha, Almería» |
| Nombre del municipio en otra lengua oficial | 2 | «Algimia de Alfara» (anuncio) y «ALGIMIA D'ALFARA» (Catastro); el INE de 2025 solo da «Algímia d'Alfara» |
| Paraje entre dos municipios | 1 | «Monforte de Lemos e Pobra de Brollón» |
| Referencia de Gipuzkoa sin provincia ni municipio | 1 | «82950960147121N» (Donostia) |
| Polígono y parcela en letra, sin provincia | 1 | «polígono ciento cuatro, parcela siete, Campillo de Llerena» |

Probado contra CartoCiudad el 2026-11-02: «Paseo de la Marina 5, Garrucha» sí y con «, Almería»
detrás no; «Callejuela del Cuartel 2, Frechilla» no y «Cuartel 2, Frechilla» sí; «avenida de
Navarra 20, Donostia» da Milagro (Navarra) y con «Donostia/San Sebastián» da Donostia.

## Decisión
1. **Clave de un nombre de lugar** (`geo/names.py`): sus palabras sin mayúsculas, tildes,
   artículos, preposiciones ni conjunciones del castellano, el catalán y el valenciano, el
   gallego y el asturiano. «Algimia de Alfara» y «Algímia d'Alfara» son «algimia alfara». Se
   usa para comparar el municipio de la oferta con el del Catastro y CartoCiudad, y para buscar
   su código INE en los candidatos de CartoCiudad (de cada candidato vale su municipio, sea
   calle, topónimo o núcleo). Lo que cambia entero entre lenguas («Donostia» y «San
   Sebastián») sigue saliendo de los nombres dobles del INE y de CartoCiudad.
2. **Un municipio que nombra dos** («X y Z», «X e Z», «X i Z»): vale cualquiera de los dos.
3. **Consultas a CartoCiudad** (`address_queries`): primero «calle número, municipio», sin
   provincia, «nº», paréntesis ni el municipio repetido, y con el municipio entero; después lo
   mismo sin el tipo de vía; por último, la dirección tal como llegó. Vale la primera que da un
   punto del municipio de la oferta.
4. **De varias referencias en un valor, la primera** con forma de referencia, como la ubicación
   de la primera finca de un lote (ADR-0034). Se sigue comprobando contra su cita.
5. **Polígono y parcela en letra** se leen como números, solo tras «polígono» y «parcela». Si
   el anuncio no dice la provincia, es la de los lugares de CartoCiudad que se llaman como el
   municipio, si todos son de la misma.
6. **Gipuzkoa sin provincia ni municipio**: «parcela (7) + siete cifras + letra», solo si la
   oferta es de Gipuzkoa; vale la única parcela vigente con ese número en cualquier municipio, y
   después se comprueba el municipio como siempre.

## Opciones consideradas
- **Cargar los nombres de municipio del INE.** El INE de 2025 da «Algímia d'Alfara», solo en
  valenciano: no habría casado con el anuncio en castellano.
- **Comparar por parecido (distancia de edición).** Aceptaría municipios distintos de nombre
  parecido; la clave solo quita palabras que no distinguen.

## Consecuencias
- Recomprobado sin LLM: de 181 a 195 lotes ubicados de 202. Cada lote nuevo cae en una sección
  del municipio que dice su anuncio (o, sin municipio, en el de su referencia).
- Quedan 7: El Frasno 1, 2, 6 y 7 (sin referencia ni parcela única), un paraje rural de Lugo, una
  referencia que el Catastro no conoce y Requena (rechazo correcto).
- Una clave sin artículos puede igualar dos municipios distintos («La Puebla» y «Puebla»). Solo
  importa si el servicio sitúa el punto justo en el otro; el riesgo es menor que el de rechazar
  todos los nombres en otra lengua.
