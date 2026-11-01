# ADR-0030: Planes con la marca del profesional

- **Estado:** aceptada (decisiones de Rodrigo, 2026-11-01)
- **Fecha:** 2026-11-01
- **Tarea:** F7.3

## Contexto
El profesional entrega el plan (ADR-0025, PDF de ADR-0026) a su cliente: tiene que llevar su marca.

## Decisión
- **Marca por organización** (`org_branding`, con Row-Level Security de ADR-0028):
  - nombre comercial (hasta 80 caracteres);
  - línea de contacto (hasta 120);
  - color principal;
  - texto de presentación (hasta 600);
  - logotipo.
  No son datos personales del cliente: no se cifran.
- **Logotipo seguro:** PNG o JPEG de hasta 2 MB. `branding/logo.py` lo abre con Pillow (ya era
  dependencia, ADR-0021), con su límite de píxeles contra imágenes que estallan al
  descomprimirlas. Lo reduce a 600 × 200 como mucho y lo vuelve a codificar en PNG: se guarda la
  imagen reescrita, nunca el fichero subido. **SVG no:** puede cargar recursos externos al
  generar el PDF. Pillow se permite en `branding/`, además de en `documents/`.
- **Color con contraste:** `#RRGGBB` con un contraste de al menos 4,5:1 sobre blanco (WCAG AA,
  texto normal). Un color más claro se rechaza diciendo por qué.
- **Dónde se ve:**
  - **PDF:** cabecera con logotipo, nombre y contacto, la presentación debajo y el color en
    títulos y líneas.
  - **Página `/plan`:** la misma cabecera, para que el profesional vea lo que va a enviar.
  Sin marca, el plan queda como hasta ahora.
- **HouseFinder, en una línea discreta** al pie del PDF: «Cifras calculadas con HouseFinder, con
  las fuentes del anexo». Mantiene la trazabilidad de las cifras y nuestra independencia; el
  anexo de fuentes no cambia.
- **Edición en `/marca`,** para cualquier cuenta de la organización (en la beta, una por
  profesional).

## Opciones consideradas
- **Marca blanca total:** el cliente no sabría de dónde salen las cifras.
- **SVG para el logotipo:** mejor calidad, pero exige sanearlo; no compensa en la beta.

## Consecuencias
- Pillow pasa a usarse en dos paquetes.
- El color del profesional solo cambia títulos y líneas: el texto sigue en negro y las cifras
  provisionales conservan su marca.
