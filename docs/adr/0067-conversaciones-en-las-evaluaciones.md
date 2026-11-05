# ADR-0067: Conversaciones en las evaluaciones del asesor

- **Estado:** aceptada
- **Fecha:** 2026-11-06
- **Decide:** Rodrigo («Sí, sigue», sobre añadir casos de conversación a `make evaluar`)
- **Completa:** ADR-0027 (evaluaciones y línea base), ADR-0063, ADR-0064 y ADR-0066.

## Contexto

`make evaluar` mide preguntas sueltas al asesor (F6.0, ADR-0027). En la web el asesor conversa
(ADR-0063, ADR-0066) y hay fallos que solo salen en una conversación. En la prueba de la web, a
«¿y con la hipoteca variable?» contestó con cifras que no eran las de la variable. Ninguna
evaluación lo habría visto.

## Decisión

1. **Una evaluación más, `conversacion`**, con varias preguntas seguidas y el historial que pone
   la API: las preguntas y los textos aceptados, con sus marcadores, hasta seis mensajes
   (ADR-0064).
2. **Tres conversaciones**, en `advisor/evaluation.py`:
   - **en el plan de una oferta:** «¿qué me queda al mes?», «¿y si suben los tipos?» y «¿y con
     la hipoteca variable?»;
   - **en «Mi plan»:** la zona de una oferta y luego «¿y está cara?»;
   - **en «Mi plan»:** «¿qué ofertas me encajan?» y luego «¿cómo me conviene alquilar la
     primera?».

   La oferta del plan es la primera de la organización de desarrollo que tiene plan completo.
   Sin perfil confirmado se saltan las que lo necesitan, y se dice.
3. **Lo que se mide en cada vuelta**, sin leer el significado del texto:
   - **herramientas:** si vuelve a pedirlas, porque los marcadores de vueltas anteriores no
     valen;
   - **texto mostrado** y **a la primera**, como en las preguntas sueltas;
   - **cifra pedida:** si cita al menos una de las cifras de lo que se pregunta. Por ejemplo, a
     «¿y con la variable?», los intereses esperados de la variable. Se compara la clave del
     marcador sin el prefijo de la oferta;
   - **misma oferta:** si las cifras de «¿y está cara?» son de la oferta de la vuelta anterior.
     Se lee del prefijo `oferta_…` de sus claves;
   - **cifras fuera de marcadores**, que tiene que ser cero, y **contradicciones de sentido**.
4. **Línea base.** Cifra pedida, misma oferta, herramientas, mostrados y a la primera no pueden
   bajar. Las contradicciones no pueden subir.

## Consecuencias

- La cifra pedida no prueba que la frase atribuya bien la cifra. Solo prueba que la que hacía
  falta está citada. Lo demás se sigue leyendo a mano en el informe (`SALIDA=…`).
- «La primera» de la búsqueda no se comprueba: `recomendar_alquiler` no pone prefijo de oferta a
  sus cifras. Solo se mide que pida la herramienta.
- Cada vuelta es una llamada al modelo: con el modelo local, unos dos minutos por vuelta.
