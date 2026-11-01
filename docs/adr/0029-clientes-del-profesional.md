# ADR-0029: Varios clientes por profesional

- **Estado:** aceptada (decisiones de Rodrigo, 2026-11-01)
- **Fecha:** 2026-11-01
- **Tarea:** F7.2

## Contexto
Hasta ahora cada organización tenía un perfil: el último confirmado (`latest_profile_id`). Un
profesional de la beta lleva varios clientes y necesita su perfil, su búsqueda y su plan por
separado.

## Decisión
- **Tabla `clients`,** con el nombre que pone el profesional («María L.», «cliente de Getafe»).
  El nombre se cifra con sobre como el perfil (ADR-0011), atado a su fila y su organización. Solo
  se descifra para enseñárselo a su organización y tiene Row-Level Security por organización
  (ADR-0028).
- **Perfiles y entrevistas llevan su cliente** (`client_id`, obligatorio). El perfil vigente de un
  cliente es el último que confirmó. Las versiones anteriores se quedan, como hasta ahora.
- **Cliente activo en una cookie** (`hf_cliente`, `HttpOnly` y `SameSite=Lax`), que la API valida
  en cada petición: el cliente tiene que ser de la organización de la sesión. Se elige con un
  selector en la barra de la web. Si la cookie falta o no vale y la organización tiene un solo
  cliente, se usa ese. Si tiene varios, la API pide elegir (409). Perfil, búsqueda, plan, PDF y
  asesor trabajan con el cliente activo.
- **Las ofertas y las rentas esperadas son del profesional** (de su organización): una oferta se
  evalúa con el perfil del cliente activo y sirve para varios clientes.
- **Quitar un cliente lo borra del todo**, con confirmación en la web: su nombre, sus perfiles y su
  entrevista (`ON DELETE CASCADE`). Es lo que pide el derecho de supresión y no deja datos que
  custodiar. Lo que hay en las copias de seguridad caduca con ellas (F7.5).

## Opciones consideradas
- **Un código sin datos personales en vez del nombre:** sin cifrar, pero menos cómodo; el
  profesional tendría que llevar la correspondencia fuera.
- **El cliente en cada URL:** permite dos clientes en dos pestañas, pero hay que pasarlo en cada
  enlace y en cada llamada.
- **Archivar en vez de borrar:** obligaría a fijar un plazo de conservación.

## Consecuencias
- Las órdenes de terminal (asesor, evaluaciones) usan el perfil más reciente de la organización,
  sea del cliente que sea.
- Un particular (F8) será una organización con un solo cliente: el mismo modelo.
- La rotación de la clave maestra (`profiles/store.rotate`) solo cubre los perfiles; los nombres
  de cliente se quedan fuera, igual que las entrevistas. Queda pendiente.
