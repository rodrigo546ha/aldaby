# Auditoría de la interfaz · 2026-11-05

Revisión de todas las pantallas tras el design system v2 (DESIGN.md, ADR-0055 y ADR-0056).

## Cómo se ha hecho
1. **Medición automática** en cada pantalla, con un escáner que se ejecuta en la propia página.
   Mide:
   - el contraste real de cada texto contra su fondo, componiendo las capas semitransparentes;
   - el texto por debajo de 13 px;
   - las mayúsculas espaciadas;
   - los objetivos de toque por debajo de 24 × 24 px (WCAG 2.2, 2.5.8);
   - las imágenes sin `alt`;
   - los saltos en el orden de los encabezados.
2. **Pantallas medidas:** portada, acceso, ofertas (mapa y lista), ficha de oferta, plan (con todo
   desplegado), añadir anuncio, perfil, supuestos, simulador, clientes, marca, agencias y textos
   legales. Tema oscuro y claro, a 1440 px de ancho.
3. **Revisión a ojo** de la disposición, la jerarquía, la coherencia y el movimiento, también en
   móvil (375 px).

## Resultado de la medición

| Comprobación | Pantallas con fallos | Qué falla |
|---|---|---|
| Encabezados en orden, un `h1`, `alt` en imágenes | ninguna | — |
| Mayúsculas espaciadas | plan | la marca «provisional» a 0,1 em (el sistema dice 0,06 em) |
| Contraste del texto | ofertas, ficha | etiqueta de canal entre 3,6:1 y 4,3:1 en los dos temas; atribución del mapa ~1,3:1 |
| Texto < 13 px | ofertas, ficha, plan | unidad de cifra («al mes») a 11,8–12,6 px; crédito de foto a 12 px |
| Objetivos < 24 px | todas | «Salir» (22 px), los cinco enlaces del pie (22 px), «Añadir un anuncio» del panel (22 px), los desplegables del plan (22–23 px) |

## Hallazgos, por gravedad

### Crítico
1. **La atribución «© OpenStreetMap» del mapa es casi invisible:** texto negro sobre el lienzo verde.
   Los estilos de MapLibre pisan los nuestros por especificidad. La licencia ODbL obliga a que se
   vea.
2. **La etiqueta de cada canal no llega a AA:** el texto de color va sobre un tinte de su mismo
   color, y se queda entre 3,6:1 y 4,3:1 en los dos temas.

### Alto
3. **Objetivos de toque por debajo de 24 px** en la barra («Salir»), el pie, el panel de ofertas y
   los desplegables («Cómo se calcula», «Fórmulas y fuentes», tipos de alquiler, notas).
4. **El anillo de foco se recorta** en las tarjetas de la lista y en los chips: los contenedores con
   desplazamiento cortan el contorno, y quien usa el teclado no ve dónde está.
5. **Las filas de chips del panel se cortan** sin indicar que se desplazan en horizontal.

### Medio
6. **Unidades y créditos por debajo del mínimo** de 13 px.
7. **Importes con «,00»** que no aportan nada («204.000,00 €»).
8. **«Añadir un anuncio»:**
   - el título de la página («Analiza un anuncio») no coincide con el del menú;
   - el estado de cada anuncio («Extrayendo», «Confirmado») es texto plano;
   - la columna de detalle vacía ocupa media pantalla.
9. **Clientes:**
   - el estado («· activo · con perfil») va en texto gris pequeño;
   - el cliente activo no se distingue del resto;
   - «Borrar» parece un enlace normal, aunque pide confirmación.
10. **Agencias:**
    - sin feeds, solo una línea gris («Aún no hay ningún feed»), sin explicar qué es ni cómo
      empezar;
    - «Quitar» tampoco se distingue como acción destructiva.
11. **En móvil, el selector de cliente de la barra** corta el nombre («Prueba suba»).

### Bajo
12. **CSS muerto** de pantallas retiradas: tarjeta de la búsqueda antigua, lista de anuncios del BOE,
    campos de lote y avisos de subastas.
13. **Nombres de la v1:** unos 160 usos en el CSS (`--raised`, `--muted`…). Funcionan como alias de
    la v2 y se pasan a los nombres nuevos al tocar cada pantalla.

## Lo que está bien y no se toca
- **Movimiento reducido:** con `prefers-reduced-motion` se anulan todas las transiciones y
  animaciones.
- **Animaciones:**
  - la entrada de página es corta (8 px, 360 ms) y solo mueve `transform` y `opacity`;
  - las fotos aparecen con un fundido;
  - los veredictos cuentan una sola vez;
  - los plegables se abren por su altura.
- **Contraste del texto de la v2:** sin fallos en las pantallas rediseñadas (ficha, plan, simulador,
  perfil y supuestos), en los dos temas.
- **Estructura:** un `h1` por página, encabezados en orden y todas las imágenes con `alt`.

## Estado
Corregidos en el commit de esta auditoría: 1 a 12. El 13 queda como migración progresiva.
