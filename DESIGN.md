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
| `--text-sm` | 14 | rótulos, pistas, metadatos, cabeceras de tabla |
| `--text-xs` | 13 | notas al pie y créditos de foto. Es el mínimo |
| `--text-2xs` | 12 | solo etiquetas en mayúsculas (canal, «provisional») |

- Titulares y cifras en **Bricolage Grotesque 500** con tracking negativo (más cerrado cuanto más
  grande). Ni negrita ni fina.
- Interfaz en **Geist**: 400 el texto, 500 los rótulos, 600 los botones y estados. Cifras tabulares
  en datos, tablas y precios.
- **Mayúsculas solo en etiquetas** de 12 px (canal, «provisional»), con 0,06 em. Navegación,
  botones, rótulos, cabeceras de tabla y estados van en frase normal.
- **Una cifra no se parte** entre líneas; su unidad, más pequeña, puede bajar.

### Espacio, radios, sombra y tamaños

- Rejilla de 4: `--sp-1` (4) … `--sp-16` (64). Dentro de un componente 8–16; entre componentes
  24–32; entre secciones 40–64.
- Radios: 4 etiquetas, 8 controles, 12 tarjetas, avisos y fotos, 16 paneles.
- Sombra: **solo** `--shadow-overlay`, para lo que flota sobre el mapa o sobre otra capa (panel y
  ficha del mapa, menús). Las tarjetas y los paneles en página no llevan sombra.
- Objetivos de toque de 44 px (`--target`); 36 px (`--target-sm`) en chips y herramientas, con 8 px
  entre ellos.

### Movimiento

Tres duraciones con la misma curva: 120 ms respuesta al toque, 220 ms cambio de estado, 360 ms
entrada de página o panel. Solo `transform` y `opacity`. Con movimiento reducido no se anima nada y
el estado final se ve al instante.

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

### Veredicto, rejilla de cifras, bloques plegables y gráficas
Siguen como en la v1, con la tipografía nueva: los rótulos en frase normal a 14 px, y las cifras de
cabecera a 36 px en escritorio y 28 en móvil.

## Pantallas

### Ofertas (`/mapa`)
Una sola lista de todos los canales (ADR-0054), en mapa o en lista. El panel tiene:
1. el recuento y su resumen («286 subastas · 2 encajan con tu plan»);
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
5. tu plan: el veredicto con tres cifras y «Ver mi plan completo», o qué falta para verlo;
6. avisos (corrección del BOE, ubicación aproximada, vivienda habitual del deudor);
7. secciones «La subasta», «El inmueble» y «Fuentes».

En escritorio, tu plan va en una columna fija a la derecha.

### Plan (`/plan/[id]`)
Foto arriba y, debajo, veredicto, temas plegables, simulador de puja y asesor, como en la v1.

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
