# ADR-0020: Perfilado con preguntas fijas, extracción con evidencia y entrevista cifrada

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.2

## Contexto
F6.2 pide un perfilado conversacional que produzca un `UserProfile` validado (ingresos, deudas,
ahorro, año de nacimiento, comunidad, hijos, objetivo, horizonte, riesgo y gestión). Son datos
personales (ADR-0011) y casi todos son cifras: ninguna puede salir del modelo (ADR-0001). En el
banco del agente (F6.0), `qwen3:8b` no seguía las instrucciones de forma fiable y `qwen3:14b`
acertaba las herramientas pero copiaba números.

## Decisión
- **Preguntas fijas.** El código elige el siguiente dato que falta (primero los obligatorios) y hace
  su pregunta, escrita de antemano en `profiles/interview.py`. El modelo no redacta preguntas.
- **El modelo solo extrae**, de la última respuesta, todos los datos que diga (si el usuario dice
  «tengo 35 años y gano 2.500 netos», rellena los dos), cada uno con una
  **cita literal de su respuesta** (`agent/profiling.py`). Se comprueba sin modelo, como en la
  extracción de anuncios (ADR-0013): la cita tiene que estar en la respuesta del usuario, no en la
  pregunta, y un número tiene que ser uno de los de la cita («40 mil» y «40k» cuentan como
  40.000; los números escritos con letras no se aceptan y el dato se vuelve a preguntar). Lo que no
  pasa se descarta con su motivo.
- **Las conversiones son código:** ingresos anuales o en catorce pagas a mensuales, edad a año de
  nacimiento (aproximado, se avisa), nombre de comunidad a código INE (`data/profiles/
  comunidades.yaml`). El modelo dice qué dijo el usuario; la cuenta la hace el código, con su
  fórmula a la vista en la confirmación.
- **Confirmación campo a campo**, como en las ofertas pegadas (F4.1): el usuario ve cada dato con
  su cita y puede corregirlo. Solo al confirmar se valida el `UserProfile` y se guarda cifrado
  (`profiles/store.py`).
- **La entrevista se guarda cifrada** (tabla `profile_interviews`, migración 0012) para poder
  retomarla: respuestas literales y borrador en un sobre (ADR-0011), con su fila y su organización
  como datos asociados. En claro solo el estado, las fechas y el perfil resultante. Las respuestas
  quedan guardadas hasta que el usuario borre la entrevista; la política de conservación se fija
  con la consulta legal (F0.6).
- **Llamada síncrona:** cada respuesta se extrae dentro de la petición (unos segundos con el modelo
  local; las respuestas son cortas). Si en F7 tarda demasiado, se pasa a la cola (ADR-0010).
- Base imponible, tipo marginal y base del ahorro **no se preguntan**: salen de los documentos
  (F6.3) o se dejan vacíos, como permite el modelo.

## Prueba con qwen3:14b (2026-10-31)
La primera entrevista real convirtió «2.300 € netos en 14 pagas» en 191,67 € al mes (el modelo dio
el periodo «año» con la cita «en 14 pagas») y aceptó «no me importa algo de riesgo» como prueba de
«no tengo deudas». También daba citas buenas con valores vacíos o basura. Se añadió:
- **El valor sale de la cita** si el modelo no da un número y la cita, que está en la respuesta,
  tiene uno solo; con varios no se elige.
- **Una opción solo vale si su cita lo dice:** «año» o «anual» para el periodo anual, una negación y
  «préstamo», «hipoteca», «deuda» o «cuota» para no tener deudas, «delegar», «gestora» o «agencia»
  para la gestión pasiva, y así con cada opción.
- **Una respuesta solo rellena huecos** de otros campos: «uno nació en 2016» (de un hijo) pisaba el
  año de nacimiento del usuario. El campo preguntado sí se puede corregir. El año de nacimiento
  tiene que ser de alguien de entre dieciocho y cien años.
- Si se pregunta por los hijos y el modelo no da nada, valen los años de cuatro cifras plausibles
  escritos en la respuesta.

Con eso, la entrevista completa sale bien en nueve de diez campos; en la gestión el modelo volvió a
equivocarse, la comprobación lo descartó y el campo queda para que el usuario lo elija. Cada
respuesta tarda entre treinta y setenta segundos con el modelo local: el proxy de la web espera
hasta tres minutos (`experimental.proxyTimeout` en `next.config.mjs`).

## Opciones consideradas
- **Que el modelo conduzca la conversación:** más natural, pero depende de que siga instrucciones;
  con los modelos que caben en el Mac no es fiable. Se puede añadir después sobre lo mismo: el
  modelo redactaría la pregunta del campo que el código elija.
- **No guardar la conversación** (el navegador reenvía las respuestas): menos datos personales, pero
  no se puede retomar. Descartada por decisión de Rodrigo.
- **Formulario sin modelo:** lo más fiable, pero no admite respuestas libres con varios datos.

## Consecuencias
- Ninguna cifra del perfil la escribe el modelo: o está en la respuesta del usuario, o la calcula el
  código desde ella, o la escribe el usuario al confirmar.
- Hace falta una clave maestra para la entrevista y el perfil: sin ella, la API responde 503 con la
  instrucción para crearla.
- `profiles/` puede importar `agent/` (la extracción); el test de arquitectura lo recoge.
