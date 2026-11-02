# ADR-0041: Particulares: lista de espera, cuenta propia y nivel gratuito

**Estado:** Aceptada · **Fecha:** 2026-11-02 · **Decide:** Rodrigo (lista de espera, marca Aldaby
y nivel gratuito con 3 planes, elegidos el 2026-11-02)

## Contexto
F8.1 pide una página de presentación y el alta de particulares, y F8.2 un nivel gratuito con el
perfil y la capacidad de compra. El plan de desarrollo dice «perfil, capacidad de compra, pocos
análisis».

Lo que había:
- **Cuentas.** Solo las da de alta el administrador, con un enlace de un solo uso (ADR-0028). No
  hay ningún servicio de correo para verificar direcciones ni restablecer contraseñas.
- **Datos.** Con un particular, Aldaby es el **responsable** de sus datos, no el encargado: los
  textos legales tienen que separar los dos casos (ADR-0039).
- **Página de inicio.** Era el simulador y pedía sesión.

## Decisión
1. **Marca.** Lo que ve el usuario dice **Aldaby**: la web, el PDF del plan, los textos legales y
   el asesor. Los identificadores internos (`housefinder`, `HOUSEFINDER_*`, `hf_*`) y el
   User-Agent que ven las fuentes públicas no cambian.
2. **Página de presentación pública en `/`.** Explica el producto y tiene un formulario de lista de
   espera. El simulador pasa a `/simulador`.
3. **Lista de espera, sin proveedor de correo.**
   - El formulario pide el correo, si es particular o profesional, y una casilla de
     consentimiento con enlace a la política de privacidad.
   - Se guarda el correo, el tipo, la versión de la privacidad aceptada y la fecha. Ni IP ni
     navegador.
   - La respuesta es siempre la misma, esté el correo ya apuntado o no.
   - El administrador ve la lista y da el alta con el enlace de un solo uso, como hasta ahora
     (`python -m housefinder.accounts espera` y `alta … --rol particular`). Al dar el alta se
     anota la fecha en la lista.
4. **Rol `particular`.**
   - Su organización es de tipo `particular` y tiene un solo perfil, el suyo. El «cliente» se crea
     solo la primera vez que lo necesita, con el nombre «Mi perfil».
   - La web le oculta Clientes, Agencias y Marca.
   - Acepta las condiciones para particulares y la privacidad, no el encargo.
5. **Textos por destinatario.** Cada texto legal lleva `audience` (`profesional`, `particular` o
   los dos). La privacidad pasa a la versión 2, con lo que se trata de un particular y de la lista
   de espera, así que las cuentas la vuelven a aceptar.
6. **Nivel gratuito** para las organizaciones particulares:
   - el perfil (entrevista), la capacidad de compra, el simulador y la búsqueda inversa entera;
   - el **plan completo** (página, PDF y explicación del asesor) de hasta **3 ofertas
     distintas**. Abrir otra vez una de esas tres no gasta otro. El límite está en
     `data/niveles.yaml`;
   - al llegar al límite, la API responde 402 con un mensaje, y la web dice cuántos quedan.

   Los profesionales de la beta no tienen límite. El pase de compra (F8.3) lo levantará.

## Opciones consideradas
- **Alta abierta con verificación por correo:** necesita un proveedor de correo, con su ADR y su
  cuenta. Se deja para cuando haya pasarela de pago (F8.3).
- **Alta abierta sin verificar:** no deja recuperar la contraseña sin pasar por el
  administrador, y se llena de cuentas falsas. Descartado.
- **Nivel gratuito sin búsqueda:** la búsqueda es lo que enseña el valor del producto, y limitar
  el plan completo basta para que el pase tenga sentido.

## Consecuencias
- Hasta F8.3, cada alta de particular pasa por el administrador: es lento, pero mide el interés
  sin coste.
- El formulario de la lista de espera es público y no lleva captcha. Si llega spam, se añade un
  límite por minuto en el proxy (Caddy) al desplegar (F7.5).
- La cuenta del particular es su propio perfil: borrar su organización borra todo lo suyo.
