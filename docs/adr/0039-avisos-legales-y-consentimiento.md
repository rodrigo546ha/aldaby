# ADR-0039: Avisos legales como datos versionados y aceptación por cuenta

**Estado:** Aceptada · **Fecha:** 2026-11-02 · **Decide:** Rodrigo («Sí, sigue con F7.4»)

## Contexto
F7.4 pide los avisos legales y el consentimiento de tratamiento de datos para la beta con
profesionales.
- **El profesional como responsable.** Trata datos de sus clientes: nombre, ingresos, deudas,
  situación familiar y documentos (ADR-0011, 0020, 0021, 0029). Para esos datos el profesional es
  el **responsable del tratamiento** y Aldaby su **encargado**, así que hace falta un contrato de
  encargo con lo que exige el artículo 28 del RGPD.
- **Aldaby como responsable.** Los datos de la cuenta del profesional (correo, contraseña y
  sesiones) los trata Aldaby como responsable, y el profesional tiene que recibir la información
  del artículo 13.
- **El aviso legal.** La Ley 34/2002 (LSSI), artículo 10, pide identificar al titular de la web.
- **Las cookies.** La web solo usa cookies técnicas: la de sesión y la del cliente activo
  (ADR-0028, 0029). Según la guía de cookies de la AEPD, las técnicas no necesitan consentimiento,
  pero sí información.
- **Lo que aún no tenemos.** Los textos los tiene que revisar un abogado (F0.6 y F8.5). Faltan los
  datos del titular (razón social, NIF, domicilio): Aldaby aún no está constituida, o no consta en
  el repositorio.

## Decisión
1. **Los textos son datos, como la normativa** (regla de oro 2). Cada documento está en
   `services/api/data/legal/<id>.md`, con una cabecera YAML que lleva:
   - `id`, `title`, `version` y `effective_from`;
   - `requires_acceptance` (si la cuenta tiene que aceptarlo);
   - `verified: false` hasta que lo revise el abogado.

   Los datos del titular van en `data/legal/titular.yaml`. Los que faltan quedan vacíos, y la
   página muestra «pendiente», nunca un dato inventado (regla de oro 4).
2. **Documentos:**
   - aviso legal;
   - condiciones de uso de la beta: Aldaby no presta asesoramiento financiero ni intermedia
     crédito inmobiliario (Ley 5/2019), las cifras son orientativas y llevan sus fuentes, y la
     comisión no toca la recomendación (regla de oro 7);
   - política de privacidad;
   - contrato de encargo del tratamiento;
   - política de cookies.

   Las condiciones, la privacidad y el encargo requieren aceptación.
3. **La aceptación es por cuenta y versión.**
   - La tabla `legal_acceptances` guarda la cuenta, el documento, la versión y la fecha. No guarda
     IP ni navegador.
   - Mientras falte aceptar la versión vigente de algún documento, la API responde 403 a todo lo
     de la organización. `/auth/me` dice qué falta y la web lleva a la página de aceptación.
   - Una versión nueva de un documento vuelve a pedir la aceptación.
   - La organización local de desarrollo (`HOUSEFINDER_DEV_ORG=1`) no pasa por esto.
4. **Información a los clientes del profesional.**
   - Dar de alta un cliente exige marcar que se le ha informado del tratamiento. Se guarda la
     fecha en `clients.informed_at`.
   - La web enlaza un modelo de cláusula informativa que el profesional puede entregarle.
   - Aldaby no recoge el consentimiento del cliente: la base del tratamiento la decide el
     profesional, que es el responsable.
5. **Pie de página** con enlaces a los cinco documentos en todas las páginas, también en las de
   acceso.
6. **Mientras `verified` sea `false`,** cada página lo dice arriba: «Borrador pendiente de revisión
   legal».

## Opciones consideradas
- **Textos en la web, como componentes:** no se versionan ni se pueden exigir desde la API.
  Descartado.
- **Banner de cookies:** no hace falta con cookies técnicas, y añadir uno de adorno confunde. Si
  llega una analítica con cookies (F8.6), otro ADR.
- **Guardar IP y navegador como prueba de la aceptación:** más datos de los necesarios. La cuenta,
  la versión y la fecha bastan como registro.

## Consecuencias
- Antes de la beta faltan los datos del titular y la revisión del abogado. Hasta entonces la web
  avisa en cada documento.
- Cada cambio de texto es un commit con versión nueva, y las cuentas lo vuelven a aceptar.
