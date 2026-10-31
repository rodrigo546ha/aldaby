# ADR-0019: Herramientas del agente

**Estado:** Aceptada (F6.4) · **Fecha:** 2026-10-31 · **Decide:** Rodrigo (datos al modelo);
el resto, por revisar
**Modifica** ADR-0014 (qué recibe el servidor del modelo) y completa ADR-0012.

## Contexto
En G7 el agente explica y ordena el plan de cada usuario. Para eso tiene que pedir cifras a los
motores: la valoración de una oferta, sus escenarios, el plan. La regla de oro 1 dice que el agente
no calcula, y un modelo abierto pequeño (ADR-0014) se inventa números con facilidad. ADR-0014 decía
además que el servidor del modelo solo recibe el texto de las ofertas, nunca datos del usuario; con
el agente eso ya no es posible.

## Decisión
- **Datos del usuario al modelo (Rodrigo, 2026-10-31: «se puede todo securizando según la
  legislación»).** El servidor propio puede recibir datos del usuario, con las condiciones del RGPD:
  - *Minimización (art. 5.1.c):* cada tarea recibe solo lo que necesita. El agente ve las cifras del
    plan y las respuestas del perfil, nunca nombre, DNI ni cuentas. Los documentos (F6.3) van solo
    al paso que extrae sus campos; el resto del agente ve los campos confirmados, no el documento.
    Nóminas y declaraciones pueden tener categorías especiales (art. 9: cuota sindical, bajas,
    asignación a la Iglesia): no se extraen.
  - *Seguridad (art. 32):* servidor propio en la UE, TLS y autenticación, sin guardar en registros
    las conversaciones ni las respuestas del modelo.
  - *Encargado del tratamiento (art. 28):* contrato con el proveedor del servidor virtual.
  - *Evaluación de impacto (art. 35) e información al usuario (art. 13):* antes de la beta (F7.4).
  - Pendiente de confirmar en la consulta legal de F0.6.
- **Cliente del LLM con herramientas.** `LLMClient.chat(messages, tools)` sobre la API compatible
  con OpenAI (`tools` y `tool_calls`; Ollama, vLLM y llama.cpp la sirven). Devuelve un texto o una
  lista de llamadas. Temperatura 0. El cliente falso devuelve turnos preparados.
- **El modelo no da números a las herramientas.** Los argumentos son referencias y opciones
  cerradas (el identificador de una oferta, un horizonte de una lista), validados con Pydantic.
  Las cifras salen de datos confirmados por el usuario, de los motores y de los parámetros. Si a una
  herramienta le falta un dato, lo dice («falta el tipo de interés»), y el agente se lo pregunta al
  usuario; nunca lo supone.
- **Lo que devuelve una herramienta:** sus `Figure` (clave, valor, unidad, rango y fórmula), hechos
  sin cifras (título, municipio, estado) y avisos. El modelo ve los valores para razonar (corrige
  ADR-0012, que decía que no), pero solo puede citarlos con marcadores: la comprobación de ADR-0012
  rechaza cualquier dígito fuera de uno, así que copiar un valor no sirve.
- **Bucle** (`housefinder/agent/loop.py`): hasta un número fijo de pasos; cada llamada se ejecuta,
  y su resultado o su error vuelve al modelo como mensaje de herramienta. Las cifras de todas las
  llamadas se juntan; el texto final se comprueba contra ellas (ADR-0012), con un reintento.
  Agotados los pasos o los reintentos, se devuelven las cifras sin explicación.
- **Las herramientas viven fuera de `agent/`** (`housefinder/advisor/`), que sigue sin importar
  motores ni base de datos: `agent/` sabe hablar con el modelo y comprobar su texto; `advisor/`
  sabe qué motores llamar con qué datos. Todas son de lectura: ninguna escribe ni envía nada.
- **Herramientas de F6.4:** ofertas confirmadas del usuario, valoración de una oferta (renta, precio,
  escenarios y lo pedido frente a lo estimado) y datos de la zona de una oferta. El plan completo
  de una oferta llega en F6.7, cuando sus supuestos (tipo de interés, vacío, seguros) tengan
  parámetro o los dé el usuario.

## Opciones consideradas
- **Que el modelo rellene los argumentos numéricos** (tipo de interés, vacío): es la forma más
  directa de colar una cifra inventada en un motor. Descartado.
- **Comprobar que cada número de un argumento aparece en un mensaje del usuario** (como la
  evidencia de ADR-0013): posible para F6.7 si hace falta que el usuario dé supuestos en la
  conversación; por ahora no hay herramientas que lo necesiten.
- **Herramientas dentro de `agent/`:** obligaría a que `agent/` importe la base de datos y los
  motores. Descartado.

## Consecuencias
- El texto de una oferta (título, anuncio pegado) llega al modelo dentro del resultado de una
  herramienta: es contenido no fiable. Va marcado como dato y las herramientas no tienen efectos,
  así que una instrucción escondida solo puede cambiar el texto, que se comprueba igual.
- Las direcciones y los títulos llevan números: el agente no puede copiarlos. Para nombrar una
  oferta hará falta un marcador `{{oferta:…}}` (F6.5).
- Un modelo pequeño puede no saber llamar a herramientas: se mide al elegir el modelo de producción.
