# ADR-0042: Analítica propia sin cookies: recuentos por día y embudo de alta

**Estado:** Aceptada · **Fecha:** 2026-11-02 · **Decide:** Rodrigo («ponte con ello», F8.6)

## Contexto
F8.6 pide «analítica de uso respetuosa con la privacidad». La salida de F8 pide además «el embudo de
conversión medido», del registro al pago.

Lo que ya hay:
- La web solo usa cookies técnicas (ADR-0039).
- El servidor no guarda registros de acceso, porque llevarían las IP (ADR-0040).
- Casi todo el embudo ya está en la base: lista de espera, altas, perfiles confirmados y planes
  completos (ADR-0041).

Lo único que falta son las visitas.

Con una analítica de terceros (Google Analytics y parecidas) habría que pedir consentimiento por
cookies y mandar datos fuera. Las que funcionan sin cookies pero con huella del navegador también
tratan datos personales.

## Decisión
1. **Recuento de visitas propio, sin cookies ni identificadores.**
   - Al cargar una página, la web envía a `/api/analytics/event` solo:
     - la ruta, normalizada (`/plan/[offer]`, no el identificador de la oferta);
     - el dominio del sitio del que viene, si es otro;
     - `utm_source`, si la URL lo trae.
   - La API suma 1 en la fila de ese día (hora de Madrid), ruta, origen y fuente.
   - **No se guarda nada más:** ni IP, ni navegador, ni hora exacta, ni sesión, ni cuenta. Con
     esos datos no se puede seguir a nadie, ni distinguir dos visitas de la misma persona.
2. **Se respeta la petición de no ser contado.** Si el navegador envía `Sec-GPC: 1` (Global
   Privacy Control) o `DNT: 1`, no se cuenta. Los robots tampoco, por su User-Agent, que se mira
   en la petición y no se guarda.
3. **Solo rutas de la web:** una lista cerrada de rutas conocidas. Cualquier otra cosa se
   descarta, para que nadie pueda escribir lo que quiera en la tabla.
4. **El embudo se calcula con lo que ya hay en la base:**
   1. visitas a la página de presentación;
   2. apuntados a la lista de espera;
   3. altas de particulares;
   4. particulares con perfil confirmado;
   5. particulares con algún plan completo.

   Cada paso dice cuántos y qué parte del anterior. Se pide con
   `python -m housefinder.analytics embudo --desde AAAA-MM-DD`. El pago (F8.3) será el último
   paso cuando exista.
5. **Textos legales.** La política de cookies ya dice que no hay cookies de analítica. La de
   privacidad explica el recuento (versión 3): no son datos personales, así que no necesita
   consentimiento.

## Opciones consideradas
- **Google Analytics, Matomo con cookies:** consentimiento, banner y datos fuera o huella. Descartado.
- **Plausible o Umami alojados aquí:** buenos, pero son otro servicio que mantener, y el embudo
  sale de nuestra base igualmente. Se pueden poner más adelante si hace falta más detalle.
- **Contar visitantes únicos con un hash diario de IP y navegador:** sigue siendo tratar la IP.
  Descartado: se cuentan visitas, no personas.

## Consecuencias
- Las visitas son páginas vistas, no personas. Recargar cuenta dos veces. Para el embudo vale:
  el paso que importa, la lista de espera, sí son personas.
- Quien bloquea el envío o pide no ser contado no aparece: las cifras se quedan cortas, nunca
  sobran.
