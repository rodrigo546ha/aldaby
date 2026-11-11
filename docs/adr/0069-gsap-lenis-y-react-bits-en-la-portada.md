# ADR-0069: GSAP, Lenis y componentes de React Bits en la portada

**Estado:** Aceptada · **Fecha:** 2026-11-11 · **Decide:** Rodrigo («usa también las librerías de
lenis y react bits» y «Sí, la portada», tras el estudio de interfaz del 2026-11-11)

## Contexto
La web no llevaba ninguna librería de interfaz ni de animación: todo el movimiento era CSS y View
Transitions (`docs/patrones-de-movimiento.md`), y `PRODUCT.md` lo fijaba como restricción. La portada
nueva pide dos cosas que CSS solo no da con el soporte de navegadores de hoy: una animación ligada al
desplazamiento que deforma un lienzo (la anilla se cierra al bajar) y un desplazamiento suave que
haga legible ese recorrido. El estudio también enseñó un plan de ejemplo en el primer pliegue, y una
cifra en la portada tiene las mismas reglas que en el resto del producto (regla de oro 1 y 4).

## Decisión
1. **GSAP** (`gsap`, `@gsap/react`) entra como dependencia de `apps/web`. Licencia estándar de GSAP,
   sin coste. Se usa donde el movimiento es una secuencia o va ligado al desplazamiento; pulsar,
   plegar y las entradas de página siguen en CSS. En React siempre con `useGSAP` y un `scope`, y
   todo dentro de `gsap.matchMedia()` con `(prefers-reduced-motion: no-preference)`: con movimiento
   reducido no se crea ninguna animación.
2. **Lenis** (`lenis`, MIT) entra para el desplazamiento suave, **solo en la portada**. Comparte
   reloj con GSAP (`gsap.ticker`). Las pantallas de trabajo (ofertas, ficha, plan, simulador,
   formularios) usan el desplazamiento del sistema. Lenis ya respeta el movimiento reducido.
3. **React Bits** no es una dependencia: sus componentes se copian al repositorio y pasan a ser
   código nuestro (MIT + Commons Clause según su README: se pueden usar dentro del producto). Cada
   uno se reduce a lo que `DESIGN.md` admite y se pasa a los tokens. El primero es `SplitText`, para
   el titular de la portada, reducido a la entrada por líneas con máscara; sin rebote, sin bucle y
   sin efecto al pasar el puntero.
4. **Las cifras del plan de ejemplo las calcula el motor.** La portada pide a `/simulate/investment`
   el mismo caso sintético que usa «Rellenar con un ejemplo» del simulador
   (`tests/fixtures/planes/sintetico-01.yaml`) y enseña tres de sus `Figure`. Lleva el rótulo «Plan
   de ejemplo» y, mientras sus reglas estén sin verificar, el aviso de provisional. Si la API no
   responde, la anilla se ve sin cifras.
5. Las tres librerías se cargan solo con la portada: el resto de la web no las descarga.

## Consecuencias
- `PRODUCT.md` deja de decir «sin librerías de UI»: dice cuáles hay y dónde.
- `DESIGN.md` gana el apartado de la portada y sus tres excepciones de movimiento (desplazamiento
  suave, animación ligada al desplazamiento y una entrada de 900 ms para el titular y las cifras).
- La portada depende de que `/simulate/investment` siga respondiendo sin sesión.
- Para leer el caso de ejemplo, la portada descarga en segundo plano el código del simulador. Si
  pesa, el ejemplo y su conversión a petición se sacan a un módulo propio.
- Llevar GSAP a otras pantallas (el veredicto del plan, la ficha de subasta) no necesita otro ADR;
  llevar Lenis fuera de la portada, sí.
