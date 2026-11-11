# Propuesta de UX: mapa, revelado progresivo, gráficas y movimiento

**Fecha:** 2026-11-03 · **Estado:** propuesta para revisar con Rodrigo · **Alcance:** `apps/web` y
lo que la API tiene que exponer para ello. Mantiene el sistema visual de `DESIGN.md` (capas de verde,
Bricolage + Geist, latón racionado): esto cambia **qué se enseña y cuándo**, no el estilo.

---

## 1. Diagnóstico: medido, no opinado

Capturas a 1440×900 y 375×812 con datos reales de la base local (perfil «Prueba subastas», una
oferta pegada confirmada y un lote del BOE).

| Pantalla | Palabras visibles | Alto de página | Lo que pesa |
|---|---|---|---|
| Plan de una oferta | 1.385 | 5.778 px (escritorio) · 11.576 px (móvil, ≈14 pantallas) | 52 cifras en 7 secciones, **40 con la etiqueta PROVISIONAL**, 52 «Cómo se calcula», 11 pasos de la hoja de ruta, bloque final de avisos con claves internas |
| Anuncios públicos | 1.528 | 4.315 px | títulos del BOE de 40–60 palabras en la lista |
| Búsqueda inversa | 749 (con 2 ofertas) | 3.364 px | por oferta: 6 cifras, avisos, 4 tipos de alquiler desplegables, supuestos, avisos otra vez |
| Ofertas (pegar enlace) | 391 | 3.022 px | formulario, lista y detalle a la vez |

Problemas de fondo, por orden de impacto:

1. **Todo se enseña al mismo nivel.** La cifra que decide (¿me renta?) tiene el mismo peso que «Registro
   de la propiedad: 226,12 €». No hay un veredicto arriba y el detalle debajo: hay una pared de cifras.
2. **La trazabilidad se enseña en vez de estar disponible.** La regla de oro 1 exige que cada cifra
   *tenga* fórmula y fuente, no que las 52 enseñen su enlace a la vez. Lo mismo con PROVISIONAL: 40 sellos
   iguales dejan de avisar de nada.
3. **La oferta está repartida en cuatro sitios.** Búsqueda, Ofertas, Anuncios públicos (BOE y Patrimonio)
   y Agencias son la misma cosa vista desde el canal por el que entra. El usuario piensa en «pisos»,
   no en canales.
4. **No hay ningún gráfico.** Las cifras que son una composición (gastos de compra, cash flow) o una
   evolución (hipoteca, revalorización, puja) se leen como listas sueltas.
5. **El asesor escribe un párrafo.** El texto del modelo sale como un bloque corrido con cifras dentro;
   no se puede escanear.
6. **Herramientas fuera de contexto.** El simulador de puja aparece en el plan de una oferta pegada que
   no es subasta (`components/Bids.tsx:21` lo trata como judicial por defecto).
7. **Movimiento:** solo hay transiciones de color de 160 ms. Al calcular, las cifras aparecen de golpe;
   al cambiar de sección, la página salta.

---

## 2. Principios de la propuesta

1. **Una pregunta por pantalla, respondida arriba.** El primer pliegue contesta; lo de debajo explica.
2. **Tres niveles de profundidad, siempre los mismos:**
   **veredicto** (encaja / no encaja + 3 cifras) → **por qué** (una gráfica por tema) →
   **detalle** (la rejilla de cifras con fórmula y fuente, plegada).
3. **La trazabilidad se pliega, no se pierde.** Cada cifra sigue siendo un `Figure` y su fórmula está a un
   toque; lo que desaparece es el enlace repetido 52 veces.
4. **Lo provisional se resume por bloque:** «7 de 9 cifras dependen de reglas sin verificar», con la
   lista al desplegar. Una cifra suelta solo lleva sello si es la única provisional de su bloque.
5. **Se omite lo que no cambia la decisión.** Si un aviso no altera ni el veredicto ni una cifra
   visible, va al panel «Calidad de los datos», no al flujo principal.
6. **Gráfica solo si hay forma.** Composición → cascada; evolución → línea; rango → banda;
   comparación de escenarios → barras. Una cifra sola sigue siendo una cifra.

---

## 3. Nueva arquitectura de navegación

Hoy: 8 secciones en la barra. Propuesta: **4 destinos**.

| Destino | Qué reúne | Para quién |
|---|---|---|
| **Mapa** (inicio de la app) | Búsqueda inversa + anuncios del BOE + ventas del Patrimonio + feeds de agencias + ofertas pegadas. «Pegar un anuncio» pasa a ser una acción del mapa, no una página | todos |
| **Mi plan** | Perfil (entrevista y documentos) + simulador libre + supuestos de búsqueda | todos |
| **Clientes** | lo de hoy | profesional |
| **Ajustes** | Marca, Agencias (alta de feeds), cuenta, tema | profesional (particular: solo cuenta y tema) |

El plan de una oferta (`/plan/[id]`) sigue con URL propia, para poder compartirlo y abrirlo desde el mapa.

---

## 4. El mapa de ofertas

### 4.1 Lo que hay y lo que falta en la API

- **Hay coordenadas guardadas:** `properties.location GEOGRAPHY(Point, 4326)`
  (`db/migrations/0001_init.sql:38`), y ya se consulta por radio para deduplicar
  (`db/offers.py:162`, `ST_DWithin`).
- **Ninguna respuesta las devuelve.** `/offers`, `/search`, `/boe/announcements`, `/sales` y
  `/listings` dan municipio y sección censal, nunca un punto (`api/search.py:51-75`,
  `api/boe.py:49-58`, `api/feeds.py:52-64`).
- **Falta:** un endpoint `GET /map/offers?bbox=oeste,sur,este,norte` que devuelva, para las ofertas
  visibles por la organización, `{offer_id, lon, lat, precisión, canal, encaja, cash_flow_mes, precio}`.
  - `precisión`: `exacta` (referencia catastral o dirección) o `aproximada` (centroide de la sección o del
    municipio). Un lote del BOE situado solo por municipio se pinta como zona, no como chincheta
    engañosa.
  - Con más de unos cientos de puntos en la caja, agrupar en el servidor (`ST_SnapToGrid` por nivel de
    zoom) y devolver grupos con recuento.
  - Las cifras del marcador (encaja, cash flow) salen de la búsqueda inversa ya calculada; el mapa no
    calcula nada (regla 1).

### 4.2 Librería y teselas (necesita ADR)

- **Librería:** MapLibre GL JS (código abierto, BSD-3). Pinta teselas vectoriales con un estilo propio, así
  el mapa lleva las capas de verde en oscuro y la arena en claro; un mapa raster de colores ajenos rompería
  el sistema visual. Se carga solo en la página del mapa (`next/dynamic`).
- **Teselas, por la regla 3 (fuentes públicas, sin proveedores comerciales):**
  1. **Preferida:** el mapa base vectorial del IGN / CNIG. Datos públicos españoles; **hay que leer sus
     condiciones y su robots.txt antes de usarlo** y confirmar si permite servirlo a terceros con estilo
     propio. No lo doy por bueno sin esa lectura.
  2. **Alternativa propia:** un extracto de OpenStreetMap de España en un fichero PMTiles servido desde el
     servidor de la beta (ADR-0040). Sin dependencia externa en tiempo de uso; licencia ODbL con atribución.
  3. Descartadas: las teselas públicas de openstreetmap.org (su política prohíbe el uso intensivo) y
     Mapbox, MapTiler o Google (proveedores comerciales).

### 4.3 Empezar donde está el usuario

- **Al abrir:** el mapa centra en el **municipio de búsqueda del perfil**, que ya conocemos, sin pedir
  nada. Así nunca se abre en blanco ni con un permiso del navegador a la cara.
- **Botón «Centrar en mí»** (icono de posición, con etiqueta accesible): pide `navigator.geolocation` y
  vuela a la posición. Si el permiso ya está concedido (`navigator.permissions.query`), centra solo.
  Pedir el permiso nada más entrar, sin contexto, hace que mucha gente lo rechace para siempre.
- **RGPD:** la posición nunca sale del navegador. A la API solo va la caja visible del mapa, que no se
  registra en logs ni en analítica.

### 4.4 Cómo se usa

- **Marcador = una pastilla con el cash flow del usuario** («+120 €/mes»), no con el precio. Lleno si
  encaja, hueco si no (la misma marca de estado que ya usa la web), y el canal con un icono pequeño.
  Nunca solo color.
- **Tocar un marcador** abre una **hoja inferior en móvil** o un **panel lateral en escritorio** con:
  título corto, foto o mapa de situación, las 3 cifras del veredicto, el motivo si no encaja y el botón
  «Ver mi plan». Nada más.
- **Filtros como chips** sobre el mapa: Encaja · Subastas · Precio hasta mi capacidad · Canal. La
  capacidad de compra del perfil fija el filtro de precio por defecto.
- **Lista sincronizada con el mapa** (botón Mapa / Lista y, en escritorio, columna a la izquierda): las
  ofertas de la zona visible, ordenadas como hoy por la búsqueda inversa. Es también la alternativa
  accesible: un mapa solo no se puede usar con lector de pantalla ni con teclado.
- **Títulos cortos:** «Alcalá de Henares · nave · lote 3» en lugar del sumario del BOE de 50 palabras,
  que pasa al detalle. El título corto se compone en la API con municipio, tipo y lote, sin LLM.

---

## 5. El plan de una oferta, simplificado

### 5.1 Primer pliegue: el veredicto

```
[ Encaja / No encaja con tu plan ]                         [Descargar PDF] [Compartir]
Calle…, Getafe · 235.000 €

  −87,80 €/mes          87.176 €            3,94 %
  tu cash flow          lo que pones        TIR a 10 años
  tras impuestos

  No encaja porque: el cash flow no llega a tu mínimo de 0 €.
  [ Lo que dice el asesor ]   [ Ver los números ]
```

Tres cifras grandes en latón, el motivo en una frase y dos acciones. En móvil cabe entero en una
pantalla.

### 5.2 Debajo: un tema por pestaña o acordeón, cada uno con su gráfica

| Tema | Gráfica | Datos | ¿Existen ya en la API? |
|---|---|---|---|
| **Compra** | Cascada: precio → ITP/IVA → AJD → notaría → registro → gestoría → **total**; y barra apilada «de dónde sale»: tu dinero frente al préstamo | `purchase_costs.*`, `financing.loan`, `cashflow.cash_invested` | **Sí**, como cifras sueltas |
| **Cada mes** | Cascada: renta → vacío → gestión → comunidad → IBI → seguros → intereses → capital → IRPF → **cash flow**. El capital se pinta aparte: no es gasto, es ahorro que se queda en el piso | cifras de `cashflow.*` y `holding_costs.*` | **Sí** |
| **Hipoteca** | Línea del capital pendiente año a año y área intereses frente a capital; fija frente a variable con la trayectoria del Euríbor | `amortization_schedule` y `RatePath` | **No:** solo existen en el motor (`engines/mortgage.py:64`, `engines/rates.py:23`) |
| **Si van mal las cosas** | Barras horizontales del cash flow: base, tipos +2 puntos y los demás escenarios de estrés que ya calcula el plan | `term.*`, `mortgage.stressed_payment`, estrés | **Sí** |
| **Al vender** | Abanico conservador / base / optimista del precio y de la TIR | `valuation.appreciation_*`, `irr.rate_*` | **A medias:** tres tasas sueltas; para el abanico año a año hace falta la serie (`engines/irr.py:210`, `yearly_cashflows`) |
| **Puja** (solo subastas) | Línea de TIR y cash flow según la puja, con la puja máxima marcada | `BidsOut.levels` (`api/plans.py:139-147`) | **Sí**, es la única serie que ya sale |
| **Riesgos** | Lista corta de «argumentos para no comprar», cada uno con su cifra como chip que abre la gráfica correspondiente | `arguments[].figure_keys` | **Sí** |
| **Pasos para comprar** | Lista de comprobación por etapas (antes / compra / después), plegada salvo la etapa actual | `roadmap` | **Sí** |

Debajo de cada gráfica, **«Ver los números»** despliega la rejilla de cifras actual con fórmula y fuente.
Ese es el tercer nivel, y ahí se conserva todo lo de hoy.

### 5.3 Lo que se quita del flujo principal

- Los 52 «Cómo se calcula»: pasan a uno por tema («Fórmulas y fuentes de este bloque»).
- Los 40 sellos PROVISIONAL: uno por tema, con el recuento.
- El bloque final de avisos con claves internas: pasa a «Calidad de los datos», plegado. Los nombres
  legibles de las reglas los tiene que dar la API (`planning/simulate.py:502` hoy concatena ids).
- El simulador de puja en ofertas que no son subasta: pasa a una acción «¿Y si fuera a subasta?» o
  desaparece.
- «Tipo de alquiler y gestión» en el plan remite a la búsqueda: se trae aquí como una fila «Recomendado:
  habitual, gestión pasiva» con el detalle plegado.

### 5.4 El contrato de las gráficas (necesita ADR)

Las gráficas tienen que cumplir la regla 1 igual que las cifras: **ningún punto lo calcula la web ni el
modelo**. Propuesta: un tipo `Series` en `core/figures.py`, hermano de `Figure`:
`{key, unit, points: [{x, y}], formula, sources, provisional}`, con `Decimal` en los valores. Las cascadas
se construyen con `Figure` que ya existen (la web solo los coloca); las líneas y las bandas necesitan
`Series` nuevas desde `amortization_schedule`, `yearly_cashflows` y los escenarios de revalorización.

**Librería de gráficas:** componentes SVG propios (cascada, línea, banda, barras: cuatro tipos). Sin
dependencia nueva, toman los colores de las variables CSS en los dos temas, pesan poco y se controlan del
todo para la accesibilidad. Recharts o visx ahorrarían algo de trabajo, pero añaden una dependencia por
cuatro gráficas.

Cada gráfica lleva:
- un resumen en una frase para lector de pantalla;
- su tabla de datos al desplegar;
- valores al pasar el ratón **y al enfocar con teclado**;
- etiquetas directas en las barras, sin leyenda lejos;
- patrón o forma además del color (encaja / no encaja, base / estrés).

---

## 6. El asesor: de párrafo a fichas

Hoy `ExplanationOut` devuelve `segments` (texto con marcadores de cifra, `api/plans.py:92-105`) y la web
lo pinta como un párrafo. Propuesta:

1. **Salida estructurada del modelo** (esquema JSON validado, como ya se hace con la extracción):
   `{veredicto, claves: [{titulo, texto, figuras: [clave]}] (máx. 3), riesgos: [...], siguiente_paso}`.
   El modelo sigue sin escribir números: escribe `{{fig:clave}}` y `agent/references.py` lo comprueba
   como hoy (ADR-0012).
2. **La web lo pinta como fichas:** una frase de veredicto, tres fichas «lo importante» con la cifra como
   chip (tocarlo abre la gráfica del tema), riesgos y el siguiente paso como botón.
3. **Se omite lo que no aporta en la salida final:** el fallo técnico se queda en una línea («El asesor no
   ha podido explicar este plan; las cifras de abajo son las del plan») y los argumentos que «no salen de
   las cifras» van plegados con su aviso.
4. **Espera:** hoy son unos 30 s con un botón. Esqueleto con la forma de las fichas y texto que entra por
   streaming cuando el servidor del modelo lo permita (ADR-0014).
5. Lo mismo en cualquier análisis con modelo (perfil, extracción de anuncios): resultado en fichas de
   campo + cita, no en lista de texto.

---

## 7. Menos texto de entrada en el resto de pantallas

| Pantalla | Cambio |
|---|---|
| Cabecera de cada sección | Título + una línea. La segunda frase de las entradillas actuales va a un «?» con globo |
| Ayudas de los formularios | Solo las que evitan un error. El resto, en «?» junto a la etiqueta |
| Simulador | Formulario por pasos (Tú → El piso → Hipoteca → Alquiler → Venta) con barra de progreso y «Rellenar con un ejemplo» arriba. Resultado = el mismo veredicto + temas que el plan |
| Búsqueda (dentro del mapa) | Tarjeta de oferta: título corto, estado, 3 cifras y «Ver mi plan». Los 4 tipos de alquiler, los supuestos y los avisos pasan al plan |
| Perfil | La entrevista ya es conversación: el borrador de la derecha se ve como fichas con su cita, plegables |
| Anuncios del BOE | Títulos cortos en la lista; el sumario oficial en el detalle |

---

## 8. Movimiento por toda la web

El sistema ya tiene una curva (`--ease: cubic-bezier(0.16, 1, 0.3, 1)`). Propuesta de tokens y usos.
Todo respeta `prefers-reduced-motion` (se queda en un fundido de 0 ms o sin animación) y nada bloquea la
interacción.

**Tokens:** `--dur-1: 120ms` (respuesta al toque), `--dur-2: 220ms` (cambios de estado),
`--dur-3: 360ms` (entradas de panel y página); salida al 65 % de la entrada; muelle solo en hojas y
paneles que se arrastran.

| Momento | Animación | Por qué |
|---|---|---|
| Cambio de sección | Fundido + subida de 8 px del contenido (`--dur-3`); la barra no se mueve | continuidad: sabes que has cambiado de sitio sin perder la barra |
| Del mapa al plan | Transición de elemento compartido: la pastilla del marcador se convierte en la cabecera del veredicto (View Transitions API, con fundido simple donde no exista) | la oferta que tocaste es la que se abre |
| Mapa | Vuelo suave al centrar en ti o en un municipio; los grupos se abren en abanico al acercar; el marcador elegido crece un 8 % | orienta en el espacio |
| Hoja / panel de oferta | Entra desde abajo (móvil) o desde la derecha (escritorio) con muelle; se cierra arrastrando o con Escape | origen claro y salida clara |
| Cifras del veredicto | Recuento de 0 al valor en 600 ms, solo la primera vez y solo las 3 grandes | el resultado «llega» |
| Gráficas | La línea se dibuja de izquierda a derecha; las barras de la cascada caen en orden con 40 ms entre una y otra | enseña el orden de la cuenta |
| Acordeones y «Ver los números» | Altura con `grid-template-rows: 0fr → 1fr` y la flecha que gira | no salta la página |
| Cargas largas (búsqueda, plan, asesor) | Esqueletos con la forma del resultado y un brillo lento, nunca un spinner en medio | la espera tiene forma |
| Botones y filas | Pulsación: escala 0,98 y vuelta; hover con el cambio de capa que ya existe | respuesta inmediata al toque |
| Aviso de guardado | Toast que entra desde abajo y se va a los 4 s, sin robar el foco | confirmación sin interrumpir |

Lo que **no** se anima: la carga inicial de páginas de trabajo, el texto corrido y nada en bucle salvo la
anilla de la portada.

---

## 9. Plan por fases

Ordenado para que cada fase se pueda usar sola y no espere a la siguiente.

| Fase | Qué | Toca la API | Necesita ADR | Tamaño |
|---|---|---|---|---|
| **U1** (hecha) | Tokens de movimiento, transición entre secciones, acordeones animados, esqueletos, pulsación de botones | No | No | pequeño |
| **U2** (hecha) | Plan «veredicto primero»: cabecera de 3 cifras, temas plegables, PROVISIONAL y fórmulas por bloque, «Calidad de los datos», puja solo en subastas | No | No | medio |
| **U3** (hecha, ADR-0048) | Gráficas con datos que ya existen: lo que cuesta y cómo se paga, estrés, fija frente a variable, abanico de la TIR y curva de puja. Componentes SVG propios | No | Sí (gráficas sin dependencia) | medio |
| **U4** (hecha, ADR-0050) | `Series` en la API: amortización, cash flow anual, revalorización año a año; gráficas de hipoteca y venta. También la cascada del cash flow mensual, que en U3 no se pudo hacer: el vacío, la gestión y los intereses no salen como cifras y las unidades mezclan año y mes | Sí | Sí (contrato `Series`) | medio |
| **U5** (hecha, ADR-0051)| Mapa: endpoint por caja con agrupación, MapLibre, teselas, geolocalización, lista sincronizada, hoja de oferta, títulos cortos | Sí | Sí (teselas y librería; leer condiciones del IGN antes) | grande |
| **U6** (hecha)| Navegación en 4 destinos y «Pegar un anuncio» como acción del mapa | No | No | pequeño |
| **U7** (hecha, ADR-0052) | Asesor en fichas con salida estructurada y etapas en directo (el texto no se puede enseñar a trozos: se comprueba entero) | Sí | Sí (esquema de salida) | medio |
| **U8** (hecha, ADR-0054) | Una sola lista de ofertas de todos los canales, también sin perfil; foto de fachada del Catastro u ortofoto del PNOA; color por forma de venta; solo los datos que deciden; fuera las secciones por canal | Sí | Sí (catálogo e imágenes) | medio |
| **U9** (hecha, ADR-0069) | Portada con un plan de ejemplo calculado por el motor alrededor de la anilla, la anilla ligada al desplazamiento (GSAP), desplazamiento suave (Lenis) y «Cómo funciona» como recorrido |

Para empezar recomiendo **U1 + U2**: no tocan la API, quitan la mayor parte del texto de entrada y dejan
el terreno listo para las gráficas y el mapa.

---

## 10. Decisiones que son de Rodrigo

1. **Teselas del mapa:** mapa base del IGN (tras leer sus condiciones) o extracto propio de OpenStreetMap
   en el servidor.
2. **Geolocalización:** empezar en el municipio del perfil con botón «Centrar en mí» (recomendado), o
   pedir el permiso al entrar.
3. **Navegación en 4 destinos:** si Anuncios públicos y Agencias dejan de ser páginas propias.
4. **Roadmap:** nada de esto está en la fase activa (F7, beta con profesionales). U1–U3 mejorarían el
   piloto F7.6; U5 encaja mejor como tarea nueva de F8, el producto para particulares.
