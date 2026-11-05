---
id: encargo
title: Contrato de encargo del tratamiento
version: 2
effective_from: 2026-11-05
requires_acceptance: true
verified: false
audience: [profesional]
---
Contrato del artículo 28 del RGPD entre el profesional (**responsable**) y el titular de
{{servicio}}, {{titular}} (**encargado**), para los datos de los clientes del profesional.

## Objeto

El encargado trata los datos de los clientes del responsable solo para prestarle el servicio:
- guardar sus perfiles;
- leer los documentos que el responsable aporte;
- calcular los planes y mostrárselos.

## Datos y personas afectadas

- **Personas:** los clientes del responsable.
- **Datos:**
  - nombre o alias;
  - año de nacimiento y comunidad de residencia;
  - ingresos, deudas, ahorro y datos fiscales (base imponible y tipo marginal);
  - años de nacimiento de los descendientes;
  - objetivos y preferencias de inversión;
  - las respuestas de la entrevista;
  - los datos que se extraigan de sus documentos;
  - las preguntas al asesor sobre sus planes y sus respuestas, que se borran a los
    {{plazo_conversaciones}} de la última pregunta.
- **Categorías especiales:** no se tratan. Los documentos se leen en memoria y no se guardan, y las
  citas no copian categorías especiales.

## Obligaciones del encargado

- Tratar los datos solo según las instrucciones del responsable, que son el uso de la herramienta.
- Confidencialidad de las personas autorizadas a tratarlos.
- **Medidas de seguridad:**
  - cifrado de perfiles, entrevistas, planes, conversaciones con el asesor y nombres;
  - separación por organización en la base de datos;
  - contraseñas con argon2id;
  - sesiones con cookie segura;
  - copias cifradas.
- **Subencargados:** el alojamiento, {{alojamiento}}. El responsable autoriza este subencargado y
  será avisado de cualquier cambio para poder oponerse.
- Ayudar al responsable a atender los derechos de los clientes: el borrado de un cliente borra su
  nombre, sus perfiles, su entrevista y sus conversaciones con el asesor.
- Avisar al responsable sin dilación de cualquier brecha de seguridad que afecte a sus datos.
- Al terminar el servicio, borrar los datos o devolverlos, a elección del responsable. Las copias
  de seguridad se borran al caducar ({{plazo_copias}}).
- Poner a disposición del responsable la información necesaria para demostrar el cumplimiento.

## Obligaciones del responsable

- Informar a sus clientes del tratamiento (puede usar la cláusula modelo) y tener una base legal
  para tratar sus datos.
- Aportar solo los datos necesarios.

## Transferencias internacionales

No hay: los datos y el modelo de lenguaje están en la Unión Europea.
