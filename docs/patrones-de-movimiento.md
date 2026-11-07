# Patrones de movimiento

Las 20 reglas de microanimación del vídeo «20 Ways to Make Beautiful AI Animations (in under 60 seconds)», de @charles.unemployed (TikTok), adaptadas a housefinder. Housefinder es Next 15 y React 19, con CSS propio en `app/tokens.css`, `app/components.css` y `app/globals.css`.

Se apoyan en los tokens que ya hay en `tokens.css`:

| Token | Valor | Para qué |
|---|---|---|
| `--ease` | `cubic-bezier(0.16, 1, 0.3, 1)` | Entradas |
| `--dur-1` | 120 ms | Respuesta al toque |
| `--dur-2` | 220 ms | Cambio de estado |
| `--dur-3` | 360 ms | Entrada de página o panel |

## Tokens que faltan

Añadir a `tokens.css`, junto a los de movimiento:

```css
:root {
  /* Lo que se mueve dentro de la pantalla (no entra ni sale): sin rebote. */
  --ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);
  /* Salidas: un 20 % más cortas que la entrada que deshacen. */
  --dur-2-out: 176ms;
  --dur-3-out: 288ms;
  /* Escalonado de listas. */
  --stagger: 30ms;
}
```

## Las 20 reglas

| # | Regla | Valor | En housefinder |
|---|---|---|---|
| 1 | Entradas con ease-out | `--ease` | Ya es la curva de la casa. Toda entrada la usa. |
| 2 | Desplegables entre 150 y 250 ms | `--dur-2` (220 ms) | Menús, selects y popovers. Nunca `--dur-3`. |
| 3 | Escalonar las filas de una lista | 30 ms entre filas | Resultados de búsqueda y listas de pisos. Tope en la décima fila. |
| 4 | Encoger al pulsar | `scale: 0.97` | Botones, tarjetas de piso, chips de filtro. |
| 5 | Estirar el pulgar que se mueve | 12 % | Interruptores (switch): el pulgar se alarga mientras viaja. |
| 6 | Escalonar lo que se asienta | 30 ms | El contenido de un panel o acordeón que se abre. |
| 7 | Arcos para mover objetos | 32 px de arco | Un elemento que viaja de un sitio a otro (p. ej., un piso a «Guardados»). |
| 8 | Un pulso para confirmar un éxito | 1 → 1,08 → 1 | «Guardado», «Copiado», alerta creada. |
| 9 | ease-in-out para moverse en pantalla | `--ease-in-out` | Lo que ya está visible y cambia de sitio o de tamaño. |
| 10 | Los popovers empiezan a 0,95 | `scale: 0.95` → 1 | Menús, popovers, tooltips. |
| 11 | Entrar desde el disparador | `transform-origin` en el botón | El menú crece desde el botón que lo abre. |
| 12 | Salir hacia el disparador | El mismo origen | Y vuelve a él al cerrarse, no se desvanece hacia el centro. |
| 13 | Sin rebote en la UI de diario | Nada de curvas que se pasen de 1 | El rebote solo en momentos de celebración. |
| 14 | No animar mientras se sostiene | Seguir el puntero | Sliders de precio y superficie, mapa, arrastres: el control va pegado al dedo. |
| 15 | Salidas un 20 % más cortas | `--dur-2-out`, `--dur-3-out` | Toda salida de menú, panel o modal. |
| 16 | Solapar el estado viejo y el nuevo | Crossfade sin hueco | «Guardar» → «Guardado» sin un instante en blanco entre los dos. |
| 17 | Máscaras para revelar y cambiar de color | `clip-path` | Barras, gráficas, el relleno de un botón que cambia de color. |
| 18 | Cruzar iconos con escala y desenfoque | `scale` + `blur` | Corazón vacío → lleno, copiar → check. |
| 19 | Elástico al pasarse del límite | Resistencia al arrastrar | Carrusel de fotos y bottom sheet en el primer y último tope. |
| 20 | Reutilizar el mismo `layoutId` | Elemento compartido | La foto de la tarjeta crece hasta la ficha del piso. |

### Choca con DESIGN.md

`DESIGN.md` dice «solo `transform` y `opacity`». Hay dos reglas que se salen de eso:
- la 17, con `clip-path`;
- la 18, con `filter: blur`.

Las dos son baratas en elementos pequeños. O se añade la excepción a `DESIGN.md` («`clip-path` y `filter` solo en elementos pequeños: iconos, barras, botones»), o se quedan fuera esas dos reglas.

## CSS listo para pegar

Todo va dentro del bloque de movimiento permitido, para que «reducir movimiento» lo apague entero.

```css
@media (prefers-reduced-motion: no-preference) {
  /* 4 · Encoger al pulsar */
  button:not(:disabled):active,
  .button-link:active,
  .card-pressable:active {
    scale: 0.97;
    transition: scale var(--dur-1) var(--ease);
  }

  /* 3 · Filas escalonadas a 30 ms (tope en la décima) */
  .stagger > * {
    animation: rise var(--dur-3) var(--ease) both;
    animation-delay: calc(min(var(--i, 0), 9) * var(--stagger));
  }

  /* 6 · Lo que se abre se asienta pieza a pieza */
  .settle > * {
    animation: settle var(--dur-2) var(--ease) both;
    animation-delay: calc(min(var(--i, 0), 3) * var(--stagger));
  }

  /* 2, 10, 11, 12, 15 · Menús y popovers */
  .popover {
    transform-origin: var(--origin, top left);
    transition:
      opacity var(--dur-2) var(--ease),
      scale var(--dur-2) var(--ease);
  }
  .popover[data-state="closed"] {
    opacity: 0;
    scale: 0.95;
    transition-duration: var(--dur-2-out);
  }

  /* 9 · Lo que se mueve en pantalla */
  .moves {
    transition:
      translate var(--dur-2) var(--ease-in-out),
      scale var(--dur-2) var(--ease-in-out);
  }

  /* 8 · Pulso de confirmación */
  .confirm {
    display: inline-block;
    animation: confirm 360ms var(--ease);
  }

  /* 17 · Revelar con máscara (izquierda a derecha) */
  .reveal {
    animation: reveal var(--dur-3) var(--ease) both;
  }

  /* 18 · Cruce de iconos con escala y desenfoque */
  .icon-swap {
    display: grid;
  }
  .icon-swap > * {
    grid-area: 1 / 1;
    transition:
      opacity var(--dur-2) var(--ease),
      scale var(--dur-2) var(--ease),
      filter var(--dur-2) var(--ease);
  }
  .icon-swap > [data-hidden] {
    opacity: 0;
    scale: 0.6;
    filter: blur(4px);
  }

  /* 5 · Pulgar del interruptor que se estira al moverse */
  .switch:active .switch-thumb {
    width: calc(var(--thumb) * 1.12);
  }
}

@keyframes rise {
  from { opacity: 0; translate: 0 8px; }
  to { opacity: 1; translate: 0 0; }
}
@keyframes settle {
  from { opacity: 0; translate: 0 4px; }
  to { opacity: 1; translate: 0 0; }
}
@keyframes confirm {
  0%, 100% { scale: 1; }
  40% { scale: 1.08; }
}
@keyframes reveal {
  from { clip-path: inset(0 100% 0 0); }
  to { clip-path: inset(0 0 0 0); }
}
```

## Cómo se usa desde React

```tsx
// 3 · Escalonado: el índice va en una variable CSS.
<ul className="stagger">
  {pisos.map((piso, i) => (
    <li key={piso.id} style={{ "--i": i } as React.CSSProperties}>
      <TarjetaPiso piso={piso} />
    </li>
  ))}
</ul>

// 8 · Pulso: un `key` nuevo en cada éxito para que se repita.
const [guardados, setGuardados] = useState(0)
async function guardar() {
  await guardarPiso(id)
  setGuardados((n) => n + 1)
}
{guardados > 0 && (
  <output key={guardados} className="confirm">Guardado</output>
)}

// 11 · 12 · El popover crece desde su botón: el origen sale de la posición.
// Con Radix o Base UI ya viene como --radix-*-transform-origin o --transform-origin:
// .popover { transform-origin: var(--transform-origin); }
```

### Elemento compartido sin librería (regla 20)

Next 15 y React 19 pueden usar la View Transitions API, sin Framer Motion:

```css
.foto-piso { view-transition-name: var(--vt-name); }
::view-transition-group(*) {
  animation-duration: var(--dur-3);
  animation-timing-function: var(--ease-in-out);
}
```

```tsx
// En la tarjeta y en la ficha, el mismo nombre para la misma foto.
<img style={{ "--vt-name": `foto-${piso.id}` } as React.CSSProperties} className="foto-piso" />
// Al navegar: document.startViewTransition(() => router.push(`/piso/${piso.id}`))
```

Sin soporte (Firefox, por ahora), la navegación es la de siempre.

### Arrastres (14 y 19)

- **14 · Mientras se arrastra, nada de `transition`.** El valor se pinta en cada `pointermove`. La transición solo se pone al soltar, para asentarse.
- **19 · Pasado el límite**, el desplazamiento se amortigua y al soltar vuelve al tope:

```ts
const elastico = (exceso: number, limite = 120) =>
  limite * (1 - 1 / (exceso / limite + 1))
```

## Comprobar antes de dar algo por hecho

- [ ] Con «reducir movimiento» activado no se mueve nada y el estado final se ve al instante.
- [ ] Ninguna curva de la UI de diario se pasa de 1, porque eso es rebote.
- [ ] Toda salida dura menos que su entrada.
- [ ] Los menús salen del botón que los abre y vuelven a él.
- [ ] Las listas largas no tardan más de 300 ms en terminar de entrar.
- [ ] En arrastres, el control va pegado al puntero.
