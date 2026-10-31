# ADR-0012: El agente escribe referencias a cifras, no cifras

**Estado:** Aceptada (D12 del plan de diseño; detalles de este ADR por revisar) ·
**Fecha:** 2026-10-31 · **Decide:** Rodrigo

## Contexto
En G7 el agente explica el plan: por qué una oferta encaja o no, qué pasa en el escenario
conservador, argumentos para no comprar. La regla de oro 1 dice que ninguna cifra que vea el usuario
la genera un LLM. Comprobarlo leyendo muestras del texto no escala, y un modelo abierto pequeño
(ADR-0014) copia, redondea o se inventa números con facilidad. D12 decidió que el agente no escriba
cifras, sino referencias a las del plan.

## Decisión
- **Marcadores.** El texto del agente nombra las cifras por su clave de `Figure`:
  `{{fig:cashflow.monthly_after_tax}}`. Una cifra con rango admite una parte:
  `{{fig:valuation.price_total:low}}`, `:high` o `:range` (el valor con su rango).
- **Comprobación mecánica, sin LLM** (`housefinder/agent/references.py`). El texto en bruto se
  rechaza si:
  1. tiene algún dígito fuera de un marcador (también años, plantas o porcentajes: si un número
     importa, es una cifra del plan; si no, sobra);
  2. un marcador nombra una clave que no está entre las cifras que recibió;
  3. pide una parte de rango a una cifra sin rango;
  4. tiene llaves `{{` o `}}` que no forman un marcador válido.
- **Render en segmentos.** El texto válido se convierte en una lista de segmentos (texto o
  referencia a una `Figure` con su parte). La API devuelve los segmentos; la web formatea cada cifra
  con `<FigureView>` (D11) y el PDF de F6.8 hará lo mismo. Python no convierte cifras en texto.
- **Si el texto no pasa:** se reintenta una vez devolviendo al modelo los problemas encontrados; si
  vuelve a fallar, se muestran las cifras sin la explicación y queda registrado para la
  evaluación (F6.9). Nunca se muestra un texto rechazado.
- **Qué recibe el agente:** las cifras con su clave, valor, unidad y rango, para que pueda razonar
  (corregido por ADR-0019). Copiarlas no sirve: cualquier dígito fuera de un marcador se rechaza,
  así que el marcador es la única forma de nombrar una cifra.

## Prueba con qwen3 (2026-10-31)
Con `qwen3-hf` el texto pasa la comprobación al segundo intento. Lo que se añadió tras las pruebas:
- **Unidad repetida** (`unidad_repetida`): una unidad detrás de un marcador («{{fig:…}} €», «… al
  mes», «… años») se rechaza, porque la web ya escribe la cifra con la suya y saldría dos veces.
- **Números tapados:** lo que el modelo lee y no puede citar (fórmulas, avisos) le llega con cada
  número cambiado por «…» (`without_numbers`); el usuario los ve enteros. Si copia «…», se rechaza.
- Cada número del texto es un problema distinto en el reintento, no solo el primero de cada tramo.
- **Límite conocido:** la comprobación no ve el significado. qwen3 llegó a llamar «valor tasado» al
  precio por m² estimado, a inventar un horizonte («en cinco años», con letras) y a poner «por
  debajo» delante de una diferencia negativa. Eso es de la evaluación de F6.9 y de la elección del
  modelo en F6.0.

## Opciones consideradas
- **Dejar que el agente escriba cifras y compararlas después con el plan:** obliga a interpretar
  formatos («1.452 €», «unos 1.500», «el 4,3 %»), y redondear o aproximar se confunde con inventar.
  Descartado.
- **Plantillas fijas sin LLM:** cumplen la regla, pero no explican ni ordenan según el perfil.
  Siguen siendo la salida de respaldo cuando el texto falla.
- **Permitir números sueltos (años, plantas):** abre la puerta a cifras sin `Figure`. Si una fecha o
  un número importa, el motor lo devuelve como cifra.

## Consecuencias
- La regla de oro 1 se cumple por construcción en el texto del agente, y la evaluación de F6.9 es
  una comprobación: dígitos fuera de marcadores y marcadores que existen en el plan.
- Redacción algo más rígida. Un número escrito con letras («dos años») no lo detecta la
  comprobación de dígitos: las instrucciones lo prohíben y F6.9 lo mide con un juego de pruebas.
- Las normas se citan por nombre, sin artículos ni números; si hiciera falta citar una regla con su
  identificador, se añadiría un marcador `{{rule:…}}` con otro ADR.
