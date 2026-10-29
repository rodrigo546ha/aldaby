# F4.3 · Portal de Subastas del BOE: condiciones y vía de datos abiertos

**Fecha:** 2026-10-29 · **Datos:** `robots.txt` y ayuda del Portal, y sumarios del BOE del 9 al 28 de
octubre de 2026 por la API de datos abiertos (17 diarios). Solo se han leído enteros los anuncios
de juzgados de la Comunidad de Madrid.

## 1. El Portal no admite acceso automático
`https://subastas.boe.es/robots.txt` (leído el 2026-10-29):

```
User-agent: *
Disallow: /
```

Prohíbe todo el sitio a cualquier agente. Ni un rastreo ni la descarga única del enlace pegado
(ADR-0015, que respeta `robots.txt`) pueden leer el Portal. Un usuario sí puede abrirlo en su
navegador y copiar el texto de una subasta.

## 2. Cada subasta tiene un anuncio en el BOE
La ayuda del Portal (`https://subastas.boe.es/ayuda.php`) dice que «al día siguiente del alta de
la subasta en el Portal se inicia la tramitación del correspondiente anuncio en el BOE, que se
publica según los intervalos de publicación de anuncios (entre tres y seis días hábiles)».

Las subastas judiciales salen en la **sección IV (Administración de Justicia)** del sumario, que
ya leemos por la API de datos abiertos. Ejemplo real (BOE-B-2026-34976):

> Sección Civil e Instrucción TI Alcañiz. Plz.n 1.- Anuncio de subasta judicial en vía de apremio
> con número de identificación 4262000006001523. Dirección electrónica:
> https://subastas.boe.es/ds.php?id=SUB-JA-2026-267510

El anuncio solo dice el juzgado, el tipo de subasta, el número del procedimiento y el enlace al
Portal. **No dice qué se subasta:** ni si es un inmueble, ni su dirección, ni su valor. El título
del sumario es solo la localidad del juzgado («MADRID», «GETAFE»).

## 3. Volumen
| | Notas |
| --- | --- |
| Diarios del BOE del 9 al 28 de octubre | 17 (8 con sección IV) |
| Anuncios de la sección IV | 708, todos «Anuncio de subasta judicial…» |
| De juzgados de la Comunidad de Madrid (por la localidad del título) | 37 (≈ 13 a la semana) |
| De ellos, en vía de apremio (`SUB-JA`) / voluntarias (`SUB-JV`) | 34 / 3 |

La sección IV sale unos días a la semana y en bloque (los sábados, unas 150–165 notas). No se sabe
cuántas de las 37 son inmuebles: el anuncio no lo dice.

Límite del método: la lista de localidades de Madrid usada para contar son los partidos judiciales
de la Comunidad escritos a mano para esta medición, no una lista oficial cargada.

No se han visto en la sección IV subastas tributarias (`SUB-AT`) ni notariales; la sección V-C
(anuncios particulares) trae anuncios de notarías, sin medir aquí.

## 4. Opciones
- **A. Avisos del BOE + texto pegado.** Guardar cada anuncio de subasta de un juzgado de Madrid
  como aviso (juzgado, tipo, número, enlace, fecha), deduplicado por el identificador `SUB-…`. El
  usuario abre el enlace en su navegador y pega el texto del lote en `/ofertas` (F4.1): extracción
  con citas y confirmación. Legal y barato; no da datos del inmueble sin el usuario.
- **B. Pedir acceso a la AEBOE.** Escribir a la Agencia Estatal BOE para preguntar por una vía de
  reutilización de los datos del Portal (descarga, API o convenio). Tarea humana.
- **C. Leer el Portal de forma automática.** Contra su `robots.txt`. Descartada.

Recomendación: A ahora y B en paralelo.
