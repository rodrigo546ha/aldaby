# F6.9 · Primera evaluación automática (2026-10-31)

Con `qwen3-14b-hf` en el Mac (ADR-0014), el juego etiquetado de `data/evaluation/` y un perfil
sintético temporal (borrado después). Orden: `make evaluar` (ADR-0027).

## Lo que destapó y se corrigió

| Métrica | Primera pasada | Tras las correcciones |
|---|---|---|
| Extracción: campos correctos | 57/141 | 102/141 |
| Extracción: valor distinto | 2 | 0 |
| Asesor: herramientas correctas | 5/8 | 8/8 |
| Asesor: textos mostrados | 7/8 | 7/8 |
| Asesor: a la primera | 5/8 | 3/8 |
| Asesor: cifras fuera de marcadores | 0 | 0 |
| Asesor: contradicciones de sentido | 0 | 0 |
| Coherencia del plan | 0 incoherencias en 1 plan | 0 en 1 |

1. **El modelo escribía la palabra «value» en el valor** y dejaba la cifra solo en la cita, o el
   número como en el anuncio («235.000 €»). Se rechazaban casi todos los campos numéricos.
   Corregido en `agent/extraction.py`: si el valor es el nombre del campo, vale el único número
   de la cita; si está escrito a la española, su único número. Las instrucciones lo prohíben.
2. **El asesor pedía al usuario el identificador de la oferta** en vez de buscarlo con
   `ofertas_guardadas`. Corregido en sus instrucciones: herramientas 8/8. A cambio, hace más
   pasos y acierta menos a la primera (reintenta), y tarda más (74 s de media).
3. **Al listar las ofertas, el asesor escribía el UUID entero en el marcador** `{{oferta:…}}` y
   el texto se rechazaba. Corregido después de esta pasada: `ofertas_guardadas` da ya el marcador
   corto de cada oferta. Queda por medir en la próxima.

## Lo que queda

- **Documentos enteros sin extraer** (Leganés, Alcorcón con precio por m², estudio de alquiler):
  el modelo devuelve casi todo vacío. Varía de una pasada a otra. Es el principal margen de la
  extracción.
- **Dirección = municipio**: cuando el anuncio no da la calle, el modelo pone el municipio en la
  dirección (seis veces). La descripción del campo ya dice «calle y número».
- **Suelo como tipo**: en el BOE, la «porción de terreno» sale sin tipo comprobado.
- La coherencia solo ha visto un plan (hay dos ofertas puntuables). Hará falta más oferta.
- La línea base guardada es la de la segunda pasada.

---

## Informe de la segunda pasada: evaluaciones con qwen3-14b-hf · 2026-10-31

## Extracción de anuncios

Correctos 102/141 campos con valor · falta 36 · distinto 0 · sobra 7 · lotes de más 0 · lotes de menos 0 · errores 0

| Campo | Correcto | Falta | Distinto | Sobra |
|---|---|---|---|---|
| address | 4 | 3 | 0 | 6 |
| bathrooms | 7 | 3 | 0 | 0 |
| built_area_m2 | 9 | 3 | 0 | 0 |
| cadastral_ref | 3 | 1 | 0 | 0 |
| community_fees | 7 | 1 | 0 | 0 |
| condition | 9 | 2 | 0 | 0 |
| deposit | 2 | 0 | 0 | 0 |
| floor | 6 | 5 | 0 | 0 |
| label | 2 | 0 | 0 | 0 |
| municipality | 9 | 5 | 0 | 0 |
| operation | 10 | 2 | 0 | 0 |
| price | 9 | 4 | 0 | 0 |
| property_type | 10 | 4 | 0 | 0 |
| province | 2 | 0 | 0 | 0 |
| rooms | 7 | 2 | 0 | 0 |
| usable_area_m2 | 2 | 0 | 0 | 0 |
| year_built | 4 | 1 | 0 | 1 |

Fallos:

- alquiler-chamberi · operation: falta (esperado 'alquiler', sale None)
- alquiler-chamberi · property_type: falta (esperado 'vivienda', sale None)
- alquiler-chamberi · price: falta (esperado 1100, sale None)
- alquiler-chamberi · year_built: sobra (esperado None, sale Decimal('2021'))
- rebajado-leganes · price: falta (esperado 185000, sale None)
- rebajado-leganes · built_area_m2: falta (esperado 78, sale None)
- rebajado-leganes · rooms: falta (esperado 3, sale None)
- rebajado-leganes · bathrooms: falta (esperado 1, sale None)
- rebajado-leganes · floor: falta (esperado '1ª', sale None)
- rebajado-leganes · condition: falta (esperado 'para reformar', sale None)
- rebajado-leganes · address: falta (esperado 'avenida de la Universidad, 12', sale None)
- rebajado-leganes · municipality: falta (esperado 'Leganés', sale None)
- rebajado-leganes · year_built: falta (esperado 1975, sale None)
- rebajado-leganes · community_fees: falta (esperado 45, sale None)
- precio-m2-alcorcon · price: falta (esperado 228000, sale None)
- precio-m2-alcorcon · built_area_m2: falta (esperado 80, sale None)
- precio-m2-alcorcon · rooms: falta (esperado 2, sale None)
- precio-m2-alcorcon · bathrooms: falta (esperado 2, sale None)
- precio-m2-alcorcon · floor: falta (esperado '3', sale None)
- precio-m2-alcorcon · condition: falta (esperado 'buen estado', sale None)
- precio-m2-alcorcon · municipality: falta (esperado 'Alcorcón', sale None)
- precio-m2-alcorcon · cadastral_ref: falta (esperado '9872023VH5797S', sale None)
- garaje-fuenlabrada · address: sobra (esperado None, sale 'Fuenlabrada')
- garaje-fuenlabrada · municipality: falta (esperado 'Fuenlabrada', sale None)
- atico-pozuelo · floor: falta (esperado 'ático', sale None)
- atico-pozuelo · address: sobra (esperado None, sale 'Pozuelo de Alarcón')
- atico-pozuelo · municipality: falta (esperado 'Pozuelo de Alarcón', sale None)
- sin-precio-alcala · address: sobra (esperado None, sale 'Alcalá de Henares')
- recomendados-parla · floor: falta (esperado '2ª', sale None)
- bajo-obra-nueva-alcorcon · floor: falta (esperado ['baja', 'planta baja'], sale None)
- bajo-obra-nueva-alcorcon · address: sobra (esperado None, sale 'Alcorcón')
- adosado-las-rozas · address: sobra (esperado None, sale 'Las Rozas de Madrid')
- adosado-las-rozas · municipality: falta (esperado 'Las Rozas de Madrid', sale None)
- estudio-alquiler-madrid · operation: falta (esperado 'alquiler', sale None)
- estudio-alquiler-madrid · property_type: falta (esperado 'vivienda', sale None)
- estudio-alquiler-madrid · price: falta (esperado 750, sale None)
- estudio-alquiler-madrid · built_area_m2: falta (esperado 35, sale None)
- estudio-alquiler-madrid · bathrooms: falta (esperado 1, sale None)
- estudio-alquiler-madrid · address: sobra (esperado None, sale 'Madrid, Lavapiés')
- boe-tgss-alcala#1 · property_type: falta (esperado 'suelo', sale None)
- boe-tgss-alcala#1 · address: falta (esperado ['Carretera M-119 (Camarma-Valdeavero), n°21', 'Carretera M-119'], sale None)
- boe-tgss-alcala#2 · property_type: falta (esperado 'suelo', sale None)
- boe-tgss-alcala#2 · address: falta (esperado ['Carretera M-119 (Camarma-Valdeavero), n°21', 'Carretera M-119'], sale None)

## Asesor

herramientas correctas 8/8 · texto mostrado 7/8 · a la primera 3/8 · cifras fuera de marcadores 0 · contradicciones 0 · tiempo medio 74 s

### ¿Está cara mi oferta de Getafe? ¿Cuánto se alquilaría?

herramientas bien · mostrado · fallo: — · 100.4 s

La renta estimada sería de [valuation.rent_monthly]. El precio estimado es de [valuation.price_total], y el anuncio pide [offer.asking_price]. El anuncio pide un poco menos que lo estimado. En [valuation.appreciation_optimistic] se podría subir el precio.

### ¿Cuánto podría revalorizarse la oferta de Getafe?

herramientas bien · mostrado · fallo: — · 94.4 s

La oferta de Getafe podría revalorizarse entre [valuation.appreciation_conservative] y [valuation.appreciation_optimistic] anualmente, según escenarios conservador y optimista. El precio estimado del inmueble es [valuation.price_total], mientras que el anuncio pide [offer.asking_price]. La renta estimada es [valuation.rent_monthly].

### ¿Qué rentabilidad bruta tendría la oferta de Getafe si la compro al precio que piden?

herramientas bien · mostrado · fallo: — · 96.3 s

La rentabilidad bruta estimada si compras al precio que pide el anuncio sería de [offer.gross_yield_at_asking]. Esta cifra se calcula con la renta estimada del inmueble dividida entre el precio pedido, sin incluir gastos ni impuestos. El rango estimado de rentabilidad bruta va desde [offer.gross_yield_at_asking] hasta [offer.gross_yield_at_asking]. El precio que pide el anuncio está dentro del rango estimado del valor del inmueble.

### ¿Cómo es la zona de mi oferta de Getafe?

herramientas bien · mostrado · fallo: — · 129.7 s

La zona de su oferta en Getafe tiene una renta bruta media por hogar de [territory.renta_bruta_media_hogar] y una renta neta media por persona de [territory.renta_neta_media_persona]. La población media de la zona es de [territory.poblacion], con una edad media de [territory.edad_media]. La renta ha subido en el último lustro, lo que sugiere una mejora económica en la zona.

### ¿Qué ofertas tengo guardadas?

herramientas bien · NO mostrado · fallo: texto_rechazado · 54.5 s

Hay un número escrito a mano («({{oferta:ed3a9482-5a52-»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («{oferta:ed3a9482-5a52-43»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («ta:ed3a9482-5a52-43ba-a8»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («:ed3a9482-5a52-43ba-a857»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («3a9482-5a52-43ba-a857-69»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («-5a52-43ba-a857-6930a173»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («2-43ba-a857-6930a173b98c»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («a-a857-6930a173b98c}}) y»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («57-6930a173b98c}}) y otr»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («s ({{oferta:5ded1059-682»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («{oferta:5ded1059-682c-4e»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («ta:5ded1059-682c-4e74-bc»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («ed1059-682c-4e74-bcfc-64»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («1059-682c-4e74-bcfc-6451»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («c-4e74-bcfc-64513409514e»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Marcador mal escrito («en Getafe ({{oferta:ed3»): el formato es {{fig:clave}}. | Hay un número escrito a mano («({{oferta:ed3a9482-5a52-»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («{oferta:ed3a9482-5a52-43»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («ta:ed3a9482-5a52-43ba-a8»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («:ed3a9482-5a52-43ba-a857»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («3a9482-5a52-43ba-a857-69»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («-5a52-43ba-a857-6930a173»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («2-43ba-a857-6930a173b98c»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («a-a857-6930a173b98c}}) y»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («57-6930a173b98c}}) y otr»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («s ({{oferta:5ded1059-682»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («{oferta:5ded1059-682c-4e»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («ta:5ded1059-682c-4e74-bc»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («ed1059-682c-4e74-bcfc-64»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («1059-682c-4e74-bcfc-6451»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Hay un número escrito a mano («c-4e74-bcfc-64513409514e»): usa un marcador {{fig:clave}} o di lo mismo sin números. | Marcador mal escrito («en Getafe ({{oferta:ed3»): el formato es {{fig:clave}}.

### ¿Qué ofertas me encajan?

herramientas bien · mostrado a la primera · fallo: — · 23.6 s

La oferta [oferta Oferta pegada] no encaja porque con la subida de tipos el cash flow no llega a tu mínimo. Su precio es de [offer.price], y su renta estimada es de [valuation.rent_monthly].

### ¿Cómo me conviene alquilar la oferta de Getafe? ¿La gestiono yo o la delego?

herramientas bien · mostrado a la primera · fallo: — · 40.1 s

La recomendación es alquilar habitualmente, ya que es el único tipo con renta pública. La gestión recomendada es activa, ya que es la que elegiste. Si delegas, el costo mensual sería de [management.habitual.delegation_cost]. Con el alquiler habitual, el cash flow mensual sería de [rental.habitual.cashflow].

### Explícame mi plan completo para la oferta de Getafe.

herramientas bien · mostrado a la primera · fallo: — · 55.3 s

El plan completo para [oferta Oferta pegada] indica que el precio de la oferta es [offer.price] y el máximo que puedes pagar es [affordability.max_price]. El cash flow mensual tras impuestos es [cashflow.monthly_after_tax], lo que significa que tendrías que poner dinero cada mes. Con la subida de tipos, el cash flow no alcanza tu mínimo. Se recomienda un alquiler habitual con gestión activa.

## Coherencia del plan

1 planes · 0 incoherencias


## Frente a la línea base

- agente.a_la_primera baja de 5 a 3
- extraccion.sobra sube de 6 a 7
