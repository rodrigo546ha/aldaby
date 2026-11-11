---
name: Aldaby
version: 2
description: Plan de inversión inmobiliaria personal en el que cada cifra dice cómo se calcula
source: apps/web/app/tokens.css
colors:
  dark:
    bg: "#0a2920"
    bg-sunk: "#071f18"
    surface: "#0f3f31"
    surface-2: "#174f3e"
    surface-hover: "#1d5b48"
    text-strong: "#ffffff"
    text-emphasis: "#eef4f1"
    text: "#dbe6e1"
    text-muted: "#b4c8bf"
    border: "rgba(234, 246, 240, 0.12)"
    border-strong: "rgba(234, 246, 240, 0.24)"
    border-control: "#6f9c8b"
    brass: "#e3a92b"
    accent-text: "#f5d68e"
    focus: "#e3a92b"
    success: "#8eddb8"
    warning: "#f2cf83"
    danger: "#ffab9b"
    info: "#a8cdff"
  light:
    bg: "#f3ead6"
    bg-sunk: "#ebdfc2"
    surface: "#fffdf8"
    surface-2: "#f7f0df"
    surface-hover: "#efe4c9"
    text-strong: "#0f3b2e"
    text-emphasis: "#173f33"
    text: "#263f37"
    text-muted: "#4a5b53"
    border-control: "#8a7c58"
    accent-mark: "#9a6a0a"
    accent-text: "#7a4f00"
    focus: "#0f3b2e"
    success: "#1a6e4c"
    warning: "#7a4f00"
    danger: "#a3301c"
    info: "#1d58a3"
  channel:
    subasta-judicial: { dark: "#f2c66b", light: "#8a5a00" }
    subasta-administrativa: { dark: "#8fbcf5", light: "#2457a3" }
    subasta-notarial: { dark: "#c9a8f5", light: "#6b44b0" }
    venta-directa: { dark: "#6fd6c4", light: "#0f6f62" }
    agencia: { dark: "#f5a3c0", light: "#a3365f" }
    tu-anuncio: { dark: "#eaf6f0", light: "#0f3b2e" }
typography:
  head: "Bricolage Grotesque 500, tracking negativo"
  ui: "Geist 400/500/600, ss01 cv11, cifras tabulares en datos"
  scale: { 2xs: 12px, xs: 13px, sm: 14px, md: 16px, lg: 18px, xl: 22px, 2xl: 28px, 3xl: 36px, 4xl: 48px }
  leading: { tight: 1.15, body: 1.55 }
spacing: [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]
rounded: { xs: 4px, sm: 8px, md: 12px, lg: 16px, pill: 999px }
targets: { default: 44px, compact: 36px }
motion: { dur-1: 120ms, dur-2: 220ms, dur-3: 360ms, ease: "cubic-bezier(0.16, 1, 0.3, 1)" }
---

# Design System: Aldaby · v2 «Claridad»

## Por qué hay una v2

La v1 («El instrumento de profundidad») apostaba por la atmósfera: un lienzo verde casi monocromo,
capas que solo cambiaban de tono, latón racionado y rótulos en mayúsculas espaciadas de 11 px. El
uso real, sobre todo con cientos de ofertas, enseñó que eso perjudica la lectura:

| Medida (2026-11-05) | v1 | v2 |
|---|---|---|
| Contraste entre el lienzo y un panel | 1,20:1 (no se distinguen) | 1,31:1 y borde |
| Contraste entre el panel y una tarjeta | 1,15:1 | 1,25:1 y borde de 3:1 |
| Texto atenuado sobre una tarjeta | 4,23:1 (no pasa AA) | 5,37:1 |
| Cuerpo de texto | 15 px | 16 px |
| Texto más pequeño | 10 px en mayúsculas | 12 px solo en etiquetas; 13 px el resto |
| Colores con significado | latón y verde | éxito, aviso, peligro, información y uno por canal |

La marca no cambia: verde portal, latón de la anilla, arena, Bricolage Grotesque y Geist. Cambia
cómo se usan.

## Principios

1. **Lo que decide, primero y grande.** En una oferta: qué es y dónde, cuánto cuesta, cuándo acaba
   y si encaja contigo. Todo lo demás, debajo y más pequeño.
2. **Legible antes que atmosférico.** Cuerpo de 16 px con interlínea de 1,55, líneas de 68
   caracteres como mucho, frases normales en vez de mayúsculas espaciadas.
3. **Las capas se ven.** Cada superficie se separa de la de debajo por tono y por borde. Lo que flota
   sobre el mapa lleva además sombra.
4. **El color significa algo y nunca va solo.** Un estado lleva su palabra o su icono. El canal
   lleva su nombre. El latón es solo para tu cifra.
5. **Accesible por defecto.** AA en todo el texto de los dos temas, foco visible, objetivos de 44 px,
   movimiento reducido respetado, todo usable con teclado y con lector de pantalla.
6. **La trazabilidad se pliega, no se pierde** (regla de oro 1). Cada cifra sigue siendo una
   `Figure` con su fórmula y su fuente a un toque.

## Tokens

La fuente de verdad es `apps/web/app/tokens.css`. Los componentes solo usan variables. Los nombres
de la v1 (`--canvas`, `--raised`, `--muted`…) siguen como alias de la v2 para el CSS que aún no se
ha pasado, pero no se escriben en CSS nuevo.

### Superficies

| Token | Papel | Oscuro | Claro |
|---|---|---|---|
| `--bg` | lienzo de la página | `#0a2920` | `#f3ead6` arena |
| `--bg-sunk` | hueco: campos, estado vacío, pie | `#071f18` | `#ebdfc2` |
| `--surface` | panel | `#0f3f31` | `#fffdf8` papel |
| `--surface-2` | tarjeta o bloque dentro de un panel | `#174f3e` | `#f7f0df` |
| `--surface-hover` | bajo el puntero | `#1d5b48` | `#efe4c9` |

**Regla de las capas.** Una superficie siempre está sobre la de debajo, nunca sobre una igual. Si
dos cosas del mismo nivel tienen que separarse, las separa un borde (`--border`) o aire, no un tono
inventado.

### Texto

`--text-strong` para titulares y cifras, `--text-emphasis` para enlaces, etiquetas de campo y
valores de datos, `--text` para texto corrido y `--text-muted` para rótulos y pistas. Los cuatro
pasan AA (4,5:1) sobre todas las superficies de su tema; el más justo es `--text-muted` sobre
`--surface-2`, con 5,37:1 en oscuro y 6,35:1 en claro.

### Bordes

`--border` separa (1 px). `--border-strong` dibuja tarjetas. `--border-control` es el borde de lo
que se toca (campos, chips, botón secundario) y llega a 3:1 (WCAG 1.4.11).

### Marca y acento

- `--brass` (`#e3a92b`): la anilla del logotipo y la selección de texto. No es color de texto.
- `--accent-text`: **tu** cifra (cash flow, puja máxima, TIR). En oscuro latón claro, en claro latón
  tostado. Nada más va en latón: ni titulares, ni fondos, ni iconos.
- `--accent-mark`: marcas que no son texto (pestaña activa, anillo de «no encaja», casillas).
- `--focus`: el anillo de foco, 2 px separado 2 px. Latón en oscuro, verde portal en claro.

### Estados

| Token | Para | Oscuro | Claro |
|---|---|---|---|
| `--success` / `-bg` | encaja, verificado, libre | `#8eddb8` | `#1a6e4c` |
| `--warning` / `-bg` | provisional, a comprobar, corrección | `#f2cf83` | `#7a4f00` |
| `--danger` / `-bg` | error, riesgo alto, ocupado | `#ffab9b` | `#a3301c` |
| `--info` / `-bg` | nota neutra, dato de la fuente | `#a8cdff` | `#1d58a3` |

Siempre con texto: «Encaja», «Provisional», «Ocupado». El fondo `-bg` es un tinte para avisos y
etiquetas; el texto encima es el color del estado.

### Cómo se vende cada oferta

Un color por canal (`--ch-*`): subasta judicial (latón), administrativa (azul), notarial (violeta),
venta directa (verde agua), agencia (rosa) y tu anuncio (neutro). Todos pasan 4,5:1 sobre
`--surface-2`. Se usan en el filo de la tarjeta, en la etiqueta del canal y en el punto del mapa,
y siempre con el nombre del canal al lado.

### Tipografía

| Token | Tamaño | Uso |
|---|---|---|
| `--text-4xl` | 48 | titular de la portada |
| `--text-3xl` | 36 | título de página; cifras de cabecera |
| `--text-2xl` | 28 | título de una ficha; cifras de cabecera en móvil |
| `--text-xl` | 22 | título de bloque; cifra de rejilla |
| `--text-lg` | 18 | entradilla; precio de tarjeta; leyenda de formulario |
| `--text-md` | 16 | cuerpo, navegación, campos |
| `--text-base` | 15 | texto de tarjetas, avisos, puntos y explicaciones |
| `--text-sm` | 14 | rótulos, pistas, metadatos, cabeceras de tabla |
| `--text-xs` | 13 | notas al pie y créditos de foto. Es el mínimo |
| `--text-2xs` | 12 | solo etiquetas en mayúsculas (canal, «provisional») |

- Titulares y cifras en **Bricolage Grotesque 500** con tracking negativo (más cerrado cuanto más
  grande). Ni negrita ni fina.
- Interfaz en **Geist**: 400 el texto, 500 los rótulos, 600 los botones y estados. Cifras tabulares
  en datos, tablas y precios.
- **Mayúsculas solo en etiquetas** de 12 px (canal, «provisional»), con 0,06 em. Navegación,
  botones, rótulos, cabeceras de tabla y estados van en frase normal.
- **Una cifra no se parte** entre líneas; su unidad, más pequeña, puede bajar y nunca baja de 13 px.
- **Importes:** siempre con separador de miles («4.000 €», también con cuatro cifras) y con
  céntimos solo si los hay («204.000 €», «89,98 €»).

### Espacio, radios, sombra y tamaños

- Rejilla de 4: `--sp-1` (4) … `--sp-16` (64), y `--sp-24` (96) solo para el final de página y la
  portada. Dentro de un componente 8–16; entre componentes 24–32; entre secciones 40–64.
- **Ningún tamaño de letra, relleno, margen, hueco ni radio va escrito en px o rem** en las hojas de
  estilo: sale de un token. Las únicas excepciones son los ajustes ópticos de 1–3 px, los tamaños
  relativos a una cifra (`em`, como la unidad «al mes») y los huecos reservados para otra pieza (los
  botones del mapa).
- **Paneles:** todo panel (veredicto, asesor, sección de la ficha, pasos del simulador) lleva el mismo
  relleno, `--panel-pad` (24 px; 20 × 16 en móvil), así el texto de dentro empieza siempre en el mismo
  sitio. El título de un tema plegable del plan empieza justo ahí: la flecha ocupa el relleno.
- **Barra de la aplicación:** por debajo de 1180 px se quitan los rótulos que se deducen («Cliente» y
  la cuenta) y se estrechan los huecos; por debajo de 920 px los destinos pasan a la barra inferior.
  Nada se sale de la pantalla a ningún ancho.
- Radios: 4 etiquetas, 8 controles, 12 tarjetas, avisos y fotos, 16 paneles.
- Sombra: **solo** `--shadow-overlay`, para lo que flota sobre el mapa o sobre otra capa (panel y
  ficha del mapa, menús). Las tarjetas y los paneles en página no llevan sombra.
- Objetivos de toque de 44 px (`--target`); 36 px (`--target-sm`) en chips, herramientas, enlaces
  sueltos (pie, «Salir») y desplegables, con 8 px entre ellos. Nada que se toque baja de 24 px,
  salvo un enlace dentro de una frase.

### Movimiento

Tres duraciones: 120 ms respuesta al toque (`--dur-1`), 220 ms cambio de estado y desplegables
(`--dur-2`), 360 ms entrada de página o panel (`--dur-3`). Con movimiento reducido no se anima nada y
el estado final se ve al instante, también al cambiar de pantalla.

- **Curvas:** las entradas, con `--ease` (arranca rápido y se posa). Lo que ya se ve y cambia de
  sitio o de tamaño (la barra de progreso del simulador), con `--ease-in-out`. Ninguna curva se pasa
  de 1: en la interfaz de diario no hay rebote.
- **Salidas:** un 20 % más cortas que la entrada que deshacen (`--dur-2-out`, `--dur-3-out`). Un
  plegable se abre en 220 ms y se cierra en 176.
- **Listas:** las filas llegan escalonadas, 30 ms entre filas (`--stagger`); a partir de la décima,
  todas a la vez, para que ninguna lista tarde más de 300 ms en empezar a enseñarse entera.
- **Lo que se abre se asienta:** el contenido de un plegable entra pieza a pieza, 30 ms entre piezas
  y hasta la cuarta.
- **Pulsar:** botones, tarjetas de oferta y chips encogen a `--press` (0,97) mientras se pulsan.
- **Menús y listas desplegables:** crecen desde el control que los abre (la lista de municipios
  desde su campo), desde 0,95, y vuelven a él al cerrarse.
- **Confirmar:** lo que sale bien late una vez (1 → 1,08 → 1): el icono de un aviso de éxito o el
  «Guardado».
- **Cambiar de estado sin hueco:** el texto de un botón que cambia («Guardar» → «Guardando…») entra
  mientras el viejo sale (`Swap`); dos iconos que se cruzan (el sol y la luna del tema) lo hacen con
  escala y desenfoque.
- **Gráficas:** las barras y la línea se revelan con una máscara de izquierda a derecha, sin
  deformarse.
- **De una pantalla a otra:** la foto de la oferta viaja del mapa a la ficha y de la ficha al plan
  (View Transitions, `AppLink morph`); una foto con nombre por página. Sin soporte del navegador, la
  navegación es la de siempre.
- **Propiedades:** solo `transform` y `opacity`, salvo `clip-path` y `filter` en elementos
  pequeños (iconos, barras de gráfica, botones), que son baratos ahí.
- **Arrastres:** mientras se arrastra no hay transición; el control va pegado al puntero (el mapa lo
  hace por sí solo).
- **La portada tiene tres excepciones** (ADR-0069), y solo ella: el desplazamiento es suave (Lenis);
  la anilla va ligada al desplazamiento y se cierra al bajar (GSAP ScrollTrigger); y el titular entra
  por líneas en 900 ms, el único movimiento de la web que pasa de 360. Con movimiento reducido no hay
  ninguna de las tres. El resto de pantallas usa el desplazamiento del sistema.
- **Dos cosas se mueven en bucle, y solo esas:** el aro de una oferta que cierra en menos de tres
  días, en el mapa (se abre y se apaga cada 2,4 s, y descansa la mitad del ciclo), y la anilla que
  gira junto a la etapa en la que está el asesor mientras trabaja. Con movimiento reducido, el aro y
  la anilla se quedan quietos.

## Componentes

### Botones
- **Principal** (`button`, `.button-link.primary`): degradado de amanecer en oscuro y verde portal
  macizo en claro, texto de 15 px en peso 600, en frase normal, 44 px de alto, radio 8. Uno por
  pantalla.
- **Secundario** (`button.secondary`, `.button-link`): transparente con `--border-control`.
- **Enlace** (`.link-button`): texto subrayado.
- Foco con anillo; pulsado al 98 %; desactivado al 50 % y sin puntero.

### Etiqueta de canal (`.ch-badge`)
12 px, mayúsculas a 0,06 em, peso 650, radio 4, texto `--ch` sobre su tinte al 16 %.

### Estado (`.status.pass` / `.status.fail`)
Punto lleno «Encaja» o anillo hueco «No encaja», con la palabra a 14 px en peso 600. Nunca solo el
punto.

### Chip de filtro (`.chip`)
36 px, radio 8, borde `--border-control`, con el recuento a la derecha; elegido con `aria-pressed`,
fondo `--surface-2` y borde en `--accent-mark`. Las filas de chips se desplazan en horizontal en el
panel y nunca parten una etiqueta.

### Tarjeta de oferta (`.listing`)
Foto cuadrada de 108 px, filo de 3 px en el color del canal, etiqueta del canal y cuándo acaba;
título (15 px, 600, dos líneas como mucho); dirección (una línea); precio en Bricolage a 19 px con
qué es («valor de subasta») y la superficie; si hay plan, una fila con el estado y tu cash flow en
latón. Fondo `--surface-2` con `--border`; bajo el puntero, `--surface-hover`; elegida, borde del
color del canal.

### Ficha resumida (`.offer-sheet`)
Flota sobre el mapa con `--shadow-overlay`: foto, canal, título, dirección, datos clave en rejilla
de dos, veredicto si hay plan y dos acciones: **«Ver la ficha»** (principal) y la fuente.

### Datos clave (`.keyfacts`)
Fila de tres o cuatro cifras grandes (rótulo de 14 px encima, valor en Bricolage a 28 px): precio o
valor de subasta, depósito, superficie y cuándo acaba. Es lo primero de la ficha.

**Cuenta atrás (`.countdown`).** Si la oferta tiene fecha de cierre y la subasta está abierta,
«cuándo acaba» es lo que queda: «Cierra en 5 d 01:10:14», con la fecha debajo. Cambia cada segundo
con cifras tabulares y sin animación. Solo con la fecha y la hora que da la fuente (hora peninsular):
sin hora, se cuentan los días; con la subasta sin abrir o suspendida, no hay reloj. El lector de
pantalla oye lo que queda en palabras.

### Cierra pronto
Una oferta **cierra pronto** si le quedan menos de tres días. Se dice igual en todas partes: la
etiqueta «Cierra hoy a las 18:00» (o «mañana», o «en 2 días») con el icono del reloj en `--warning`,
en la tarjeta, en la ficha resumida y en la cabecera de la ficha; el aro que late en su punto del
mapa (y en el grupo que la contiene); y el recuento del panel («6 cierran en menos de 3 días»).

### Puja máxima (`.maxbid`)
En la columna «Tu plan» de la ficha de una subasta. Se calcula al pulsar «Calcular mi puja máxima»,
no al abrir la ficha, porque cuenta como abrir el plan completo (ADR-0041). Enseña tu puja máxima en
latón a 36 px, una frase que dice qué no incluye (cargas y coste de posesión), tu cash flow al mes a
cada puja como barras que se descubren de izquierda a derecha (las que no cumplen, apagadas y con
«no cumple»), cómo se calcula y el enlace al simulador de puja del plan para ajustarla.

### Lista de datos (`.facts`)
`dl` en dos columnas (rótulo a 14 px en `--text-muted`, valor a 16 px en `--text-emphasis`), filas
separadas por `--border`. En móvil, el rótulo encima del valor. Un dato que no consta no se escribe:
no se rellena con «—» salvo en tablas.

### Aviso (`.callout`)
Bloque con radio 12, tinte del estado de fondo, borde izquierdo de 3 px del color del estado, icono
de 20 px y texto de 15 px. Variantes `info`, `warning`, `danger` y `success`. Un aviso tiene una
frase y, si hace falta, una acción.

### Cronología de la subasta (`.timeline`)
Pasos en vertical (publicada, en puja, cierra), con el actual marcado en latón y la fecha y hora a
la derecha. Solo con fechas que da la fuente.

### Panel de sección (`.section-card`)
Panel `--surface` con radio 16 y 24 px de relleno, título en Bricolage a 22 px y, si hace falta,
una línea de explicación en `--text-muted`.

### Formulario por pasos (`.stepper`)
Para formularios largos (el simulador):
- **Arriba:** «Paso n de m», una barra de progreso de 4 px en `--accent-mark` y los pasos como
  píldoras con su número. El actual va relleno, el hecho con el número en `--success` y el que tiene
  errores en `--danger`, además de un texto para el lector de pantalla.
- **En cada paso:** lo obligatorio en una rejilla de dos columnas y lo opcional plegado en «Más
  datos».
- **Abajo:** «Anterior» y «Siguiente: (paso)»; en el último, «Calcular el plan».
- **Al calcular con errores:** un resumen enlazado arriba que recibe el foco, y cada error junto a su
  campo.

### Campo con unidad (`.input-affix`)
La unidad (€, %) dentro del campo, a la derecha, en `--text-muted`, sin entrar en el valor. La
explicación va debajo, enlazada con `aria-describedby`; un ejemplo nunca va como texto de ayuda
dentro del campo (`placeholder`) si puede confundirse con un dato.

### Buscador de municipio (`.combobox`)
Patrón combobox de WAI-ARIA: se escribe el nombre y aparecen hasta doce municipios del INE con su
provincia. Flechas para moverse, Intro para elegir, Escape para cerrar. Guarda el territorio de las
reglas, no el texto.

### Conversación (`.transcript`)
La pregunta, a la izquierda en `--surface-2`; tu respuesta, a la derecha con un tinte del latón. La
pregunta actual lleva un filo de latón. Encima, el recuento de datos obligatorios con su barra.

### Veredicto (`.verdict`)
Lo primero del plan y del resultado del simulador. Arriba, si encaja o no, el título y la dirección.
Debajo, en dos columnas en escritorio:
- **A la izquierda, tu cifra:** tu cash flow tras impuestos en latón a 48 px, y a su lado, más
  pequeñas y sin latón, lo que pones y la TIR. Debajo, «Tu cash flow si las cosas van peor»: una
  fila por escenario que ya calcula el motor (subida de tipos, renta baja de la zona), con la cifra
  de hoy, la flecha y la nueva.
- **A la derecha, la cascada (`.cascade`):** de la renta del primer año a lo que te queda, una fila
  por partida (rótulo, barra que flota entre lo acumulado antes y después, importe). Cada fila se
  toca y enseña debajo, sobre `--bg-sunk`, su fórmula y sus fuentes. El total es una cifra de la API,
  no una suma hecha en la web. Las barras se revelan en orden, como el resto de gráficas.

En móvil y en el simulador, la cascada va debajo de las cifras.

### Rejilla de cifras, bloques plegables y gráficas
Siguen como en la v1, con la tipografía nueva: los rótulos en frase normal a 14 px, y las cifras de
cabecera a 36 px en escritorio y 28 en móvil.

### Explicaciones (`components/Explain.tsx`)
Todo texto que explica algo en la ficha, en el plan y en el simulador sale de estas piezas, nunca
como párrafo suelto ni como lista con viñetas del navegador. El texto viene de la API y no se
reescribe: solo se ordena y se viste.
- **Entradilla (`.lede`):** una o dos frases a 15 px en `--text-muted`, a la medida de lectura
  (68 caracteres). Presenta lo que viene debajo.
- **Rótulo (`.explain-head`):** 14 px seminegrita en `--text-strong` («De dónde salen», «La compra»).
- **Puntos (`.points`):** una sola tarjeta `--surface` con una fila por punto separada por un filete,
  y el icono del tono a la izquierda: `info`, `warning`, `success`, `danger` o un punto neutro. Si
  la frase de la API empieza por «Algo: …», «Algo» va de título en `--text-strong` y el resto debajo
  en `--text-muted`. Si la frase cita una fuente, el enlace va al pie del punto.
- **Pasos (`.step-list`):** número en un anillo de latón de 28 px, un hilo vertical que los une,
  título en seminegrita, lo que hay que hacer en `--text-muted` y el enlace a su fuente.
- **Cambios (`.changes-list`):** una fila por cifra: el nombre a la izquierda; a la derecha el valor
  de hoy en gris, una flecha de latón y el valor nuevo en `--text-strong`.
- **Cita de la fuente (`.cite-block`):** el texto literal del anuncio sobre `--bg-sunk`, con un filo
  de latón de 2 px a la izquierda, plegado a cinco líneas con «Leer entero», y debajo de dónde sale.
- **Fórmula (`.formula`):** sobre `--bg-sunk`, una línea por cláusula y los operadores (−, ×, /, =)
  en `--accent-text`.
- **Fuentes:** nunca el identificador interno. Cada fuente se enseña con su nombre («ITP de la
  vivienda usada · Comunidad de Madrid»), su cita legal o de dónde salen los valores, y el enlace
  oficial diciendo de quién es (BOE, Catastro, INE…). Los nombres los da `GET /sources`. Se agrupan
  en «Tus datos», «Normas», «Parámetros», «Datos públicos», «Modelos» y «Supuestos», cada grupo con su
  recuento y plegado a cuatro. En un tema del plan, cada cifra lleva su fórmula y los números de sus
  fuentes («Fuentes 1–8, 18»), y debajo va la lista numerada una sola vez, como el anexo del PDF.
  Dentro de una tarjeta estrecha, la lista es compacta: solo nombres, y el detalle al pasar el
  puntero.

## Pantallas

### Portada (`/`)
El primer pliegue enseña el producto: el titular, la anilla y, alrededor de ella, tres cifras de un
plan de ejemplo (tu cash flow en latón, la cuota y la TIR). Las cifras las calcula el motor con el
caso de ejemplo del simulador; debajo, una línea dice qué piso es y, si alguna regla está sin
verificar, que son provisionales. Las tarjetas de las cifras flotan sobre la anilla, así que llevan
`--shadow-overlay`. En móvil la anilla va arriba, pequeña, y las cifras debajo del texto. «Cómo
funciona» es un recorrido: una línea de `--accent-mark` avanza con el desplazamiento y cada número
se enciende al llegar.

### Ofertas (`/mapa`)
Una sola lista de todos los canales (ADR-0054), en mapa o en lista. El panel tiene:
1. el recuento y su resumen («286 subastas · 2 encajan con tu plan · 6 cierran en menos de 3 días»);
2. la búsqueda por municipio, calle o provincia;
3. el orden (recomendadas, acaban antes, precio de menos a más y de más a menos);
4. los filtros por forma de venta y por tipo, con su recuento;
5. las tarjetas.

Sin perfil la lista se ve igual y una línea dice qué falta para ver el plan.

### Ficha de una oferta (`/oferta/[id]`)
De arriba abajo:
1. volver a las ofertas;
2. canal y estado, título, dirección y lugar;
3. fotos (fachada y vista aérea) con su crédito;
4. datos clave;
5. tu plan: el veredicto con tres cifras y «Ver mi plan completo», o qué falta para verlo; en una
   subasta, además, tu puja máxima;
6. avisos (corrección del BOE, ubicación aproximada, vivienda habitual del deudor);
7. secciones «La subasta», «El inmueble» y «Fuentes».

En escritorio, tu plan va en una columna fija a la derecha.

### Simulador (`/simulador`)
Formulario por pasos a la izquierda (hasta 520 px) y tu plan a la derecha, fijo al bajar. Antes de
calcular, la columna dice qué vas a ver. En móvil, el resultado va debajo y se lleva a la vista al
calcular.

### Perfil (`/perfil`)
- **Sin entrevista:** una tarjeta con los tres pasos (contestas, revisas, confirmas) y el aviso de
  cifrado.
- **Con entrevista:** la conversación a la izquierda y el borrador a la derecha, cada dato con su
  origen («De tu respuesta», «Corregido por ti») o «Falta».
- **Confirmado:** aviso de éxito y «Ver las ofertas que encajan».

### Supuestos (`/busqueda`)
Una tarjeta con los supuestos sin fuente pública, en rejilla, cada uno con su unidad y para qué
sirve.

### Plan (`/plan/[id]`)
Foto arriba y, debajo, el veredicto con la cascada, el asesor, el simulador de puja y los temas
plegables.

## Accesibilidad (lista de comprobación)

- Texto ≥ 4,5:1 y bordes de control ≥ 3:1 en los dos temas (medidos con `tokens.css`).
- Foco visible en todo lo que se toca; el foco no queda tapado por el panel ni por la barra.
- Objetivos de 44 px (36 en chips y herramientas, con 8 de separación).
- Cada imagen informativa con `alt`; las decorativas con `alt=""`. Los iconos junto a texto, con
  `aria-hidden`.
- Estado, canal y riesgo nunca solo por color.
- Encabezados en orden (`h1` → `h2` → `h3`), un `h1` por página.
- Recuentos y resultados que cambian, en una región `aria-live="polite"`.
- El mapa tiene la lista como alternativa completa con teclado y lector de pantalla.
- Con `prefers-reduced-motion`, nada se mueve.

## Do's and Don'ts

### Do
- **Do** poner primero lo que decide y en grande: precio, cuándo acaba, si encaja.
- **Do** separar cada capa por tono y borde, y dar sombra solo a lo que flota.
- **Do** escribir en frase normal los botones, la navegación y los rótulos.
- **Do** acompañar cada color de estado o canal con su palabra.
- **Do** usar los tokens; si falta uno, añadirlo a `tokens.css` con su contraste medido.

### Don't
- **Don't** escribir texto por debajo de 13 px, salvo las etiquetas en mayúsculas de 12 px.
- **Don't** usar mayúsculas espaciadas en botones, navegación, rótulos ni titulares.
- **Don't** poner latón en titulares, fondos o iconos: es solo para tu cifra.
- **Don't** poner dos superficies iguales una sobre otra ni inventar un tono a mano.
- **Don't** rellenar un dato que no consta, ni enseñar texto de la fuente que pueda llevar nombres
  de personas (ver ADR-0054, posesión).
- **Don't** cambiar los colores de la anilla y del texto del logotipo, estirarlo ni darle sombra.
