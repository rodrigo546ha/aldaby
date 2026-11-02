---
name: Aldaby
description: Plan de inversión inmobiliaria personal en el que cada cifra dice cómo se calcula
colors:
  abyss-canvas: "#0b2c23"
  abyss-sunk: "#071f18"
  portal-raised: "#0f3b2e"
  portal-raised-2: "#164838"
  line: "rgba(234, 246, 240, 0.1)"
  line-strong: "rgba(234, 246, 240, 0.2)"
  strong-white: "#ffffff"
  mist: "#eaf6f0"
  sage-text: "#bccdc5"
  sage-muted: "#8fa79c"
  stat-glow: "#f5d68e"
  brass: "#e3a92b"
  mark-toasted: "#9a6a0a"
  warn-bg: "rgba(227, 169, 43, 0.12)"
  warn-text: "#f2cf83"
  error: "#ff9f8c"
  pass: "#8eddb8"
  cta-mint: "#d4f5e6"
  cta-sand: "#f6ebd0"
  cta-brass: "#f2c66b"
  ring-far: "#6fc29c"
  sand-canvas: "#f6ebd0"
  sand-sunk: "#ecdcb6"
  paper-raised: "#fffaee"
  sand-raised-2: "#f1e3c4"
  ink-line: "rgba(15, 59, 46, 0.13)"
  ink-line-strong: "rgba(15, 59, 46, 0.26)"
  ink-strong: "#0f3b2e"
  ink-mist: "#173f33"
  ink-text: "#2b4a40"
  ink-muted: "#4f6359"
  stat-ink: "#7f5300"
  warn-bg-light: "rgba(227, 169, 43, 0.2)"
  warn-ink: "#5f3d00"
  error-ink: "#a8321f"
  pass-ink: "#1f7a55"
  ring-near-light: "#c8901a"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(3rem, 7.4vw, 6rem)"
    fontWeight: 500
    lineHeight: 0.96
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Bricolage Grotesque, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 500
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  stat:
    fontFamily: "Bricolage Grotesque, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "-0.04em"
    fontFeature: "\"tnum\""
  title:
    fontFamily: "Bricolage Grotesque, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  figure:
    fontFamily: "Bricolage Grotesque, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.02em"
    fontFeature: "\"tnum\""
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "\"ss01\", \"cv11\""
  lead:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "0.12em"
  button:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    letterSpacing: "0.08em"
  hint:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.45
rounded:
  badge: "4px"
  control: "6px"
  notice: "12px"
  panel: "16px"
spacing:
  field: "6px"
  sm: "12px"
  md: "16px"
  form: "20px"
  gutter: "24px"
  panel: "28px"
  column: "40px"
  intro-top: "56px"
  section: "72px"
  page-end: "112px"
  page: "1320px"
components:
  button-primary:
    textColor: "{colors.abyss-canvas}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "44px"
  button-primary-light:
    backgroundColor: "{colors.ink-strong}"
    textColor: "{colors.strong-white}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "44px"
  button-secondary:
    textColor: "{colors.strong-white}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.portal-raised-2}"
  hero-cta:
    textColor: "{colors.abyss-canvas}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 28px"
    height: "56px"
  input:
    backgroundColor: "{colors.abyss-sunk}"
    textColor: "{colors.strong-white}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "42px"
  panel:
    backgroundColor: "{colors.portal-raised}"
    rounded: "{rounded.panel}"
    padding: "28px"
  well:
    backgroundColor: "{colors.abyss-sunk}"
    rounded: "{rounded.panel}"
    padding: "28px"
  warnings:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn-text}"
    rounded: "{rounded.notice}"
    padding: "16px 20px 16px 38px"
  badge-provisional:
    textColor: "{colors.warn-text}"
    typography: "{typography.label}"
    rounded: "{rounded.badge}"
    padding: "3px 6px"
  nav-link:
    textColor: "{colors.sage-muted}"
    typography: "{typography.label}"
    height: "44px"
  nav-link-active:
    textColor: "{colors.strong-white}"
  headline-figure:
    textColor: "{colors.stat-glow}"
    typography: "{typography.stat}"
    padding: "24px 24px 20px"
  figure:
    textColor: "{colors.strong-white}"
    typography: "{typography.figure}"
    padding: "16px 20px"
---

# Design System: Aldaby

## Overview

**Creative North Star: "El instrumento de profundidad"**

Aldaby se lee como un instrumento bajo el agua: un lienzo verde muy oscuro en el que las superficies no flotan sobre sombras, sino que suben o bajan de tono. Lo que se escribe está hundido, lo que agrupa está elevado y lo que importa brilla en latón. El sistema parte del estilo Auros que eligió Rodrigo (lienzo verde abisal, capas sin sombra, etiquetas en mayúsculas espaciadas, cifras grandes destacadas) y lo lleva a la marca Aldaby: el verde portal es la capa elevada, el latón de la anilla sustituye al rosa fósforo y la arena es el lienzo del tema claro.

La densidad es de herramienta de trabajo, no de folleto: páginas de 1320 px, dos columnas (formulario a la izquierda, resultados a la derecha), cifras separadas por filetes finos en lugar de tarjetas. El color se raciona. Casi todo el texto es blanco, bruma o salvia; el latón solo marca las cifras de cabecera, el foco y la sección activa. El único degradado del sistema es el del botón principal. El tema oscuro es el predeterminado; el claro (arena con tinta verde portal) sigue al sistema o al interruptor y conserva todas las capas.

La confianza es el propósito visual: cada cifra lleva al lado su «Cómo se calcula» plegado y, si depende de algo sin verificar, su sello PROVISIONAL. Nada de eso se esconde para que la pantalla quede más limpia.

**Key Characteristics:**
- Profundidad por color en tres capas (hundida, lienzo, elevada) y cero sombras de elevación.
- Bricolage Grotesque 500 con tracking negativo para titulares y cifras; Geist para interfaz y datos tabulares.
- Etiquetas en mayúsculas espaciadas 0,12 em que nombran cosas: navegación, leyendas, cabeceras de tabla, rótulos de cifra.
- Latón racionado: cifras de cabecera, foco, sección activa, anilla.
- Cifras en rejilla rayada con filetes, nunca en tarjetas iguales.
- Un único degradado, el del botón principal.

## Colors

Verdes abisales casi monocromos con un solo metal cálido; en claro, arena con tinta verde.

### Primary
- **Latón de la anilla** (brass): el acento de marca. La anilla del logotipo en los dos temas, la selección de texto y, en oscuro, el foco visible.
- **Marca** (`--mark`): el tono de las marcas que no son texto: subrayado de la sección activa y de la pestaña elegida, anillo hueco del estado «no encaja», marcador de la hoja de ruta, casillas y cursor. En oscuro es el latón; en claro, **Latón tostado de marca** (mark-toasted, `#9a6a0a`), que llega a 3,99:1 sobre arena (WCAG 1.4.11 pide 3:1).
- **Brillo de cifra** (stat-glow): el latón aclarado para texto. Las cifras de cabecera a 40 px, las referencias a cifras en el texto del asesor y la confirmación de la lista de espera. En claro pasa a **Latón tostado** (stat-ink), que sí llega a AA sobre arena.

### Secondary
- **Degradado de amanecer** (cta-mint → cta-sand → cta-brass, `linear-gradient(90deg, #d4f5e6 0%, #f6ebd0 48%, #f2c66b 100%)`): solo el relleno del botón principal y del botón de la portada en el tema oscuro, con texto en el verde del lienzo. En claro se aplana a verde portal macizo con texto blanco.
- **Verde lejano** (ring-far) y latón de anilla (cta-brass como ring-near): los dos tonos de puntos de la anilla animada de la portada. En claro: ring-near-light y verde portal.

### Neutral
- **Abismo** (abyss-canvas): lienzo de página, barra de la aplicación y fondo de la barra fija de acciones del simulador. También el color de `theme-color` del navegador.
- **Abismo hundido** (abyss-sunk): campos de formulario, estado vacío, panel del asesor, lista de espera, citas legales y pie. Es el hueco.
- **Verde portal** (portal-raised): la capa elevada, paneles de formulario, tarjetas de oferta y cabecera de marca. Es el verde de marca.
- **Verde portal alto** (portal-raised-2): hover de botón secundario y de filas de lista, burbuja de respuesta en la entrevista.
- **Blanco** (strong-white): titulares, cifras normales, valor de los campos.
- **Bruma** (mist): enlaces, texto destacado, etiquetas de campo, celdas de tabla.
- **Salvia** (sage-text): texto corrido.
- **Salvia apagada** (sage-muted): pistas, rótulos de cifra, navegación inactiva, cabeceras de tabla.
- **Filetes** (line, line-strong): separadores de 1 px; el fuerte para bordes de controles y para enmarcar la fila de cifras de cabecera.
- **Estado**: aviso (warn-bg con warn-text), error (error) y «encaja» (pass). En claro cada uno tiene su tinta oscura (warn-ink, error-ink, pass-ink).
- **Tema claro**: arena (sand-canvas) de lienzo, arena hundida (sand-sunk), papel (paper-raised) para la capa elevada, arena alta (sand-raised-2), y tintas ink-strong, ink-mist, ink-text, ink-muted.

### Named Rules
**The Brass Ration Rule.** El latón es para la cifra que importa, el foco y la sección activa. Ni fondos, ni titulares, ni iconos decorativos. El texto en latón siempre es stat-glow (oscuro) o stat-ink (claro), nunca brass, que sobre arena o papel no llega a AA.

**The One Gradient Rule.** El único degradado de la interfaz es el del botón principal en el tema oscuro. Ningún otro fondo, borde ni texto lleva degradado; en claro tampoco ese.

**The Ring Is Brass Rule.** En el logotipo la anilla es siempre `var(--brass)` y la palabra y el soporte siguen a `currentColor`. No se intercambian, no se tiñen y no llevan sombra.

## Typography

**Display Font:** Bricolage Grotesque (eje de tamaño óptico, servida con next/font; reserva Geist)
**Body Font:** Geist (reserva ui-sans-serif, system-ui, -apple-system, Segoe UI)

**Character:** Bricolage es la letra del logotipo: en peso 500 y con tracking negativo da escala sin gritar. Geist lleva todo lo que se lee de cerca, con las variantes ss01 y cv11 y cifras tabulares en campos, tablas y cifras.

### Hierarchy
- **Display** (500, clamp(3rem, 7.4vw, 6rem), 0,96, −0,04 em): solo el titular de la portada.
- **Headline** (500, 2.75rem, 1,02, −0,035 em; 2.125rem por debajo de 640 px): el título de cada sección de la aplicación. Los titulares de bloque de la portada usan clamp(2rem, 4vw, 3rem) con la misma línea y tracking.
- **Stat** (500, 2.5rem, 1, −0,04 em, en stat-glow): las cifras de cabecera del plan. La unidad («al mes», «años») va aparte a 0,5 em.
- **Title** (500, 1.5rem, 1,15, −0,02 em): títulos de resultados y bloques. Escalones intermedios: 2rem en la cabecera del plan, 1.75rem en la de una oferta, 1.375rem en subtítulos y textos legales, 1.25rem en grupos (−0,015 em).
- **Figure** (500, 1.375rem, 1,1, −0,02 em): cada cifra de la rejilla. Unidad a 0,62 em.
- **Body** (400, 15px, 1,5): todo el texto de interfaz. Las entradillas usan **Lead** (1.0625rem, 1,55, máx. 62ch) y el texto del asesor 1.0625rem con interlínea 1,7 a 72ch.
- **Label** (500, 11–12px, 0,12 em, MAYÚSCULAS): navegación, leyendas de formulario, cabeceras de tabla, rótulos de cifra de cabecera, estados y enlaces del pie. El sello PROVISIONAL es la variante de 10px y peso 600.
- **Button** (500, 13px, 0,08 em, MAYÚSCULAS): botones; el de portada a 0,1 em.
- **Hint** (400, 12.5px, 1,45): pistas, errores, rangos y «Cómo se calcula».

### Named Rules
**The Medium Only Rule.** Todos los titulares y cifras grandes van en Bricolage 500. Ni negrita ni fina; la jerarquía la dan el tamaño y el tracking, que se cierra más cuanto más grande es la letra.

**The Number Never Breaks Rule.** Una cifra no se parte nunca entre líneas: el número va en una pieza sin cortes y su coletilla de unidad, más pequeña, puede bajar debajo.

**The Tracked Label Rule.** Las mayúsculas espaciadas nombran un control o un dato (sección, leyenda, columna, cifra, estado). No se usan como antetítulo encima de un titular.

## Layout

Página centrada de 1320 px con márgenes laterales de 24 px (16 px por debajo de 640 px); `main` termina con 112 px de aire. Cada sección abre con una cabecera de 760 px de ancho máximo (56 px arriba, 40 abajo; 36/28 en móvil). Debajo, una rejilla de dos columnas con 40 px de separación: formulario de 300–440 px a la izquierda y resultados a la derecha; por debajo de 920 px pasa a una columna con 32 px. En escritorio el panel de detalle se queda fijo al bajar, y la barra de acciones del simulador también se queda fija abajo, sobre el lienzo con un filete arriba.

Ritmo: 6 px entre etiqueta y campo, 16–20 px entre campos, 32 px entre bloques de resultados, 40 px entre secciones del plan. La portada usa bloques de 72 px separados por un filete y una lista de espera con 112 × 72 px de relleno. Textos largos a 46–72ch.

Puntos de corte observados: 560 px (tablas con desplazamiento, pares de datos en una columna), 640 px (márgenes y barra compacta), 920 px (dos columnas a una) y 960 px (la navegación se desplaza en horizontal con un desvanecido a la derecha).

## Elevation & Depth

Plano y por capas de color. No hay ninguna sombra de elevación: la profundidad la marcan tres tonos (abyss-sunk debajo, abyss-canvas como lienzo, portal-raised encima, y portal-raised-2 para el hover). Lo elevado agrupa (paneles de formulario, tarjetas de oferta); lo hundido recibe (campos, estados vacíos, el panel del asesor, la lista de espera, el pie). Un campo hundido dentro de un panel elevado es el patrón más característico.

### Shadow Vocabulary
- **Filete de rejilla** (`box-shadow: 1px 0 0 var(--line), 0 1px 0 var(--line)`): no es una sombra sino la forma de dibujar los filetes de 1 px entre celdas de la rejilla de cifras. Es el único `box-shadow` del sistema.

### Named Rules
**The Depth by Color Rule.** Si algo tiene que destacar, cambia de capa; no gana una sombra. En claro las capas se invierten en valor (papel arriba, arena hundida abajo) pero mantienen el mismo papel.

**The Well Rule.** El campo es el hueco donde se escribe: fondo hundido con filete fuerte, también dentro de un panel elevado. En la lista de espera, que ya es hundida, el campo baja al lienzo.

## Shapes

Dos radios hacen casi todo: 16 px para paneles, tarjetas, estado vacío y lista de espera; 6 px para botones, campos, selector de tema y filas de lista. Los avisos usan 12 px y el sello PROVISIONAL 4 px. Los paneles no llevan borde; los controles sí (1 px line-strong). Los separadores son filetes de 1 px, y el indicador activo un trazo de 2 px. La burbuja de respuesta de la entrevista tiene la esquina inferior derecha a 6 px y las demás a 16. El chevrón de los plegables está dibujado con dos bordes de 1,5 px girados, sin icono.

## Components

### Buttons
Sobrios, de instrumento: mayúsculas espaciadas y sin icono.
- **Shape:** esquinas de control (6px), 44 px de alto, 22 px de relleno lateral.
- **Primary:** degradado de amanecer con texto abyss-canvas en oscuro; verde portal macizo con texto blanco en claro. Uno por pantalla.
- **Hover / Focus:** brillo `brightness(1.07)` en oscuro y `brightness(1.4)` en claro; al pulsar baja 1 px; foco con contorno de 2 px en latón (verde portal en claro) separado 2 px. Desactivado al 50 %.
- **Secondary:** transparente, texto blanco, filete fuerte de 1 px; en hover sube a portal-raised-2.
- **Link button:** texto bruma subrayado con filete fuerte, sin mayúsculas; en hover el subrayado toma el color del texto.
- **Botón de portada:** el mismo degradado, 56 px de alto y 28 px de relleno.

### Chips
- **Sello PROVISIONAL:** 10px, peso 600, 0,12 em, borde de 1 px en `currentColor` con texto warn-text, radio de 4px. Siempre visible junto al rótulo de la cifra.
- **Estado de fila:** marca en una celda fija con etiqueta en mayúsculas de 11px. Encaja: punto lleno de 9 px en pass. No encaja: anillo hueco de 1,5 px en `--mark`. Sin dato: solo la etiqueta en salvia apagada.

### Cards / Containers
- **Corner Style:** paneles a 16px.
- **Background:** portal-raised para agrupar (formularios, tarjetas de la búsqueda inversa, marca); abyss-sunk para recibir (asesor, vacío, lista de espera).
- **Shadow Strategy:** ninguna (ver Elevation & Depth).
- **Border:** ninguno.
- **Internal Padding:** 28 px; 24 px en los grupos de campos.

### Inputs / Fields
- **Style:** fondo hundido, filete fuerte de 1 px, radio de control (6px), 42 px de alto, texto blanco con cifras tabulares, etiqueta en bruma a 13,5 px encima y unidad en salvia apagada.
- **Hover:** el filete pasa a salvia apagada.
- **Focus:** contorno de 2 px en latón separado 1 px y el filete desaparece.
- **Error:** filete en el color de error y mensaje a 12,5 px debajo.
- **Select:** sin aspecto nativo, flecha propia de 12 × 8 en salvia apagada.

### Navigation
Barra de dos pisos sobre el lienzo con un filete abajo. Arriba, el logotipo a la izquierda (26 px de alto, 22 en móvil) y a la derecha el cliente activo (selector de 34 px con etiqueta en mayúsculas), la cuenta y el interruptor de tema (cuadrado de 34 px, radio de 6, filete fino). Abajo, las secciones en mayúsculas de 12 px a 0,12 em separadas 28 px: inactivas en salvia apagada, en hover y activas en blanco, la activa con un trazo de 2 px en `--mark` pegado al filete. Por debajo de 960 px la fila se desplaza y se desvanece por la derecha; la sección activa se desplaza a la vista. Las pestañas internas repiten el mismo lenguaje.

### Rejilla de cifras
La firma de la aplicación. Cada cifra es rótulo, valor, rango opcional y un «Cómo se calcula» plegado con la fórmula y las fuentes. Las cifras se ordenan en una rejilla automática (celdas de 220 px o más) separada por filetes. La fila de cabecera usa celdas de 190 px o más, rótulos en mayúsculas en bruma, valores en stat-glow a 40 px y filetes fuertes arriba y abajo; los rótulos reservan dos líneas para que todos los «Cómo se calcula» queden alineados.

### Avisos
Bloque con fondo de aviso, texto warn-text a 14 px y radio de 12. Un aviso que enumera cuatro o más reglas se pliega en una línea con su recuento.

### Anilla de la aldaba
Solo en la portada: la anilla del logotipo dibujada como un toro de puntos en un lienzo que gira despacio, con los tonos ring-near y ring-far del tema. Se queda quieta con movimiento reducido y no se dibuja fuera de pantalla. En móvil baja a 200 px y sube encima del titular.

## Do's and Don'ts

### Do:
- **Do** separar capas por tono: abyss-sunk, abyss-canvas, portal-raised, portal-raised-2 (en claro sand-sunk, sand-canvas, paper-raised, sand-raised-2).
- **Do** poner los campos hundidos dentro de paneles elevados, con filete fuerte de 1 px y radio de 6px.
- **Do** escribir cada cifra con su rótulo, su «Cómo se calcula» plegado y, si toca, su sello PROVISIONAL.
- **Do** separar las cifras con filetes de 1 px en rejilla, y reservar stat-glow a 40 px para la fila de cabecera.
- **Do** usar Bricolage 500 con tracking negativo para titulares y cifras, y Geist con cifras tabulares para todo lo demás.
- **Do** marcar el estado de una fila en una celda fija (punto lleno, anillo hueco, solo texto), sin mover la maquetación.
- **Do** mantener un solo botón principal por pantalla; lo demás, secundario o enlace.
- **Do** usar la curva `cubic-bezier(0.16, 1, 0.3, 1)` a 160 ms para hover y foco, y anular las transiciones con movimiento reducido.

### Don't:
- **Don't** usar sombras para elevar paneles, tarjetas ni botones; el único `box-shadow` permitido es el filete de 1 px de la rejilla de cifras.
- **Don't** poner borde a los paneles ni convertir la rejilla de cifras en tarjetas iguales.
- **Don't** escribir texto en `brass` sobre arena, papel o blanco: el texto latón en claro es stat-ink.
- **Don't** añadir un segundo degradado ni llevar el del botón al tema claro.
- **Don't** poner antetítulos en mayúsculas encima de los titulares, aunque la referencia Auros los use.
- **Don't** usar negrita ni pesos finos en Bricolage.
- **Don't** cambiar los colores de la anilla y del texto del logotipo, estirarlo ni añadirle sombra.
- **Don't** ocultar ni atenuar el sello PROVISIONAL para limpiar una pantalla.
