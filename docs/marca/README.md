# Marca: Aldaby

Nombre elegido el 2 de noviembre de 2026 para sustituir a HouseFinder. El código y los textos
del producto siguen llamándose HouseFinder hasta que se confirmen el dominio y la marca
(ver «Pendiente»).

## El nombre

La aldaba es la argolla de metal con la que se llama a la puerta. En castellano, «tener buenas
aldabas» es tener a alguien con influencia de tu parte. Eso es el producto: alguien que llama a
la puerta de cada oferta por el usuario y que no cobra del vendedor (regla de oro 7, ADR-0036).
La «-y» final lo hace nombre de producto, como Housfy o Cabify, y lo separa de la palabra común.

- Se escribe **Aldaby**, con mayúscula inicial, en el texto corrido. El logotipo va en minúsculas.
- Se pronuncia /al·dá·bi/.
- Lema de trabajo: «Llama antes de comprar.»

## El símbolo

Una aldaba vista de frente: el soporte arriba, la anilla de latón y el clavo donde golpea. Está
dibujado sobre una rejilla de 64 y se lee bien a 16 px.

## Colores

| Nombre | Hex | Uso |
|---|---|---|
| Verde portal | `#0F3B2E` | Color principal: texto del logotipo, fondos de marca, icono de la app |
| Latón | `#E3A92B` | Solo la anilla y algún acento. No usarlo para texto sobre blanco: no llega al contraste AA |
| Arena | `#F6EBD0` | Fondos suaves |
| Blanco | `#FFFFFF` | Fondo por defecto y negativo del logotipo |

## Tipografía

El logotipo es Bricolage Grotesque ExtraBold (peso 800, tamaño óptico 96) con un tracking de
−0,045 em, ya convertido a trazos: los SVG no dependen de ninguna fuente instalada. La fuente
tiene licencia SIL Open Font License 1.1.

## Ficheros

| Fichero | Para qué |
|---|---|
| `aldaby-logo.svg` | Logotipo horizontal sobre fondo claro |
| `aldaby-logo-negativo.svg` | Logotipo horizontal sobre verde portal u otro fondo oscuro |
| `aldaby-logotipo.svg` | Solo la palabra |
| `aldaby-simbolo.svg` | Solo el símbolo, sobre fondo claro |
| `aldaby-simbolo-negativo.svg` | Solo el símbolo, sobre fondo oscuro |
| `aldaby-icono-app.svg` | Icono de la app (cuadrado redondeado verde) |
| `favicon.svg` | Favicon; cambia a blanco en modo oscuro |
| `png/` | Exportaciones: icono a 1024 y 180 px, favicon a 32 px y logotipo a 1200 px de ancho |

## Uso

- Margen libre alrededor del logotipo: como mínimo el diámetro del soporte (la bola de arriba).
- Tamaño mínimo: 80 px de ancho para el logotipo horizontal y 16 px para el símbolo.
- No cambiar los colores de la anilla y del texto entre sí, no estirar y no añadir sombras.

## Regenerar

`herramientas/generar_marca.py` genera todos los SVG a partir de la fuente variable de Google
Fonts (`BricolageGrotesque[opsz,wdth,wght].ttf`, en `github.com/google/fonts`, carpeta
`ofl/bricolagegrotesque`). La fuente no se guarda en el repositorio.

```bash
services/api/.venv/bin/python -I docs/marca/herramientas/generar_marca.py ruta/BricolageGrotesque.ttf docs/marca
```

Los PNG se exportan con `rsvg-convert` (Homebrew `librsvg`).

## Pendiente

1. Registrar `aldaby.com` y `aldaby.es` (y si se quiere `.app` e `.io`). El 2 de noviembre de 2026
   no tenían servidores DNS, pero eso no garantiza que estén libres.
2. Buscar «Aldaby» en la OEPM y en la EUIPO (TMview), clases 36 y 42, y solicitar la marca.
3. Ajustar a mano el espacio entre letras del logotipo: el generador aplica tracking, no el kerning
   por pares de la fuente.
4. Renombrar el producto en la web, el PDF del plan y la documentación cuando lo anterior esté
   hecho.
