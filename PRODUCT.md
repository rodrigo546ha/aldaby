# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Profesionales en la beta privada (F7):** intermediarios hipotecarios, asesores y agencias que
  preparan planes para varios clientes desde la oficina, a menudo con el cliente delante o
  compartiendo pantalla. Trabajan con un selector de cliente activo y repiten tareas a diario.
- **Particulares (F8, más adelante):** quien quiere invertir en vivienda y necesita saber qué puede
  comprar y qué le rinde a él, no al inmueble.

## Product Purpose

Aldaby (nombre interno: HouseFinder) encuentra oportunidades de inversión inmobiliaria en España y
genera para cada usuario un plan personal: capacidad de compra, hipoteca, cash flow tras impuestos,
tipo de alquiler, gestión activa o pasiva, pruebas de estrés, escenarios normativos y hoja de ruta
de compra. El éxito es un plan en el que el usuario confía porque cada cifra se puede comprobar.

## Positioning

La rentabilidad que se calcula es la del usuario, con su hipoteca, su IRPF y su tiempo. Aldaby es
independiente: no vende activos y no cobra del vendedor; si hay comisión se declara y nunca entra en
el orden ni en el plan (ADR-0036).

## Operating Context

Secciones de la web: simulador, clientes, perfil (entrevista y documentos), búsqueda inversa,
ofertas pegadas por el usuario, anuncios públicos (BOE, Patrimonio), feeds de agencias, marca del
profesional, plan de una oferta, acceso y textos legales. El plan sale también en PDF con la marca
del profesional.

## Capabilities and Constraints

- Ninguna cifra la genera un LLM: toda cifra es un `Figure` con fórmula y fuentes, y la web enseña
  «cómo se calcula» y el aviso PROVISIONAL.
- Textos de usuario en español; importes en euros con formato español.
- Next.js (App Router) en `apps/web`, sin librerías de UI; estilos en `app/globals.css`.

## Brand Commitments

- Nombre público **Aldaby**; logotipo en minúsculas. Activos y guía en `docs/marca/`.
- Colores de marca: verde portal `#0F3B2E`, latón `#E3A92B` (nunca texto sobre blanco), arena
  `#F6EBD0`, blanco.
- Logotipo en Bricolage Grotesque ExtraBold, convertido a trazos.
- Referencia visual elegida por Rodrigo el 2 de noviembre de 2026: el estilo «Auros» (lienzo oscuro
  verde, superficies por capas sin sombras, etiquetas en mayúsculas espaciadas, cifras grandes
  destacadas), adaptado a la paleta y tipografía de Aldaby, igual en todas las secciones. Tema oscuro
  por defecto y versión clara.

## Evidence on Hand

No hay testimonios, clientes ni métricas publicables. No inventarlos.

## Product Principles

1. La IA explica; los motores calculan. La interfaz nunca presenta una cifra sin su origen.
2. Lo provisional se ve: un dato sin verificar siempre lleva su aviso.
3. La recomendación es la mejor para el usuario, nunca la que más nos paga.
4. Datos personales con cuidado: nada sensible en URL ni a la vista sin necesidad.

## Accessibility & Inclusion

WCAG 2.1 AA: contraste de texto, foco visible, formularios con etiqueta y errores asociados.
