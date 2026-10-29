# F4.4 · Qué deja fuera el filtro de títulos de la sección V

**Fecha:** 2026-10-29 · **Datos:** sumarios del BOE del 9 al 28 de octubre de 2026 (17 diarios) y
los diarios citados por las correcciones (2, 7, 20 y 21 de octubre), por la API de datos abiertos.

## Método
Anuncios de la sección V con venta, subasta o enajenación en el título que el filtro anterior no
guardaba. El filtro anterior pedía la palabra de venta y después «inmueble», «vivienda», «finca»,
«local» o «piso». Se han leído enteros los que podían ser inmuebles.

## Resultado
Nueve anuncios con venta en el título quedaban fuera. Seis no son inmuebles: vehículos del
Ejército, chatarra, depósitos de un puerto, aeronaves abandonadas, objetos decomisados y un
contrato de venta de entradas. Tres sí:

| Anuncio | Qué es | Por qué quedaba fuera |
| --- | --- | --- |
| BOE-B-2026-32556 (7/10) | Subasta de Patrimonio del Estado en Valencia, por lotes | El título dice «bienes patrimoniales» |
| BOE-B-2026-33407 (14/10) | Anula el lote 17 (finca rústica) de la subasta de Hacienda en Asturias | Es un cambio de una subasta, y «anulación» no estaba entre las correcciones |
| BOE-B-2026-34907 (26/10) | Excluye una finca rústica de la subasta de Hacienda en Aragón | «finca» va antes que «subasta», y «exclusión» no estaba entre las correcciones |

## Cambios
- **Filtro de anuncios** (`ingestion/boe.py`): venta y bien en cualquier orden, y más palabras de
  bien (solar, parcela, terreno, edificio, nave, garaje, trastero, «bienes patrimoniales»).
  En los 17 diarios medidos no añade ningún anuncio nuevo ni ningún falso positivo: los seis que no
  son inmuebles siguen fuera.
- **Correcciones** (`offers/corrections.py`): también anulación, exclusión, suspensión y
  modificación; la cita «BOE nº 251»; y, sin página, el anuncio se elige entre las subastas del
  mismo departamento por el número de expediente o, si no, por las palabras del título que solo
  comparte uno de ellos.

Con los cambios, los cinco cambios de subastas del periodo se resuelven:

| Corrección o cambio | Anuncio corregido | Cómo | ¿Se guarda? |
| --- | --- | --- | --- |
| 33407 (Asturias) | 31848 | Único anuncio de Hacienda ese día | Sí |
| 34907 (Aragón) | 32775 | Cuatro subastas de Hacienda; solo una dice «Aragón-Zaragoza» | Sí |
| 35104 (Valencia) | 32556 | Página 52908 | Sí |
| 35167 (Salamanca) | 34188 | Página 55514 | Sí |
| 35103 (Ejército) | 34258 | Única subasta del departamento ese día | No: vende vehículos y material |

Al aplicarlo a la base de desarrollo apareció otro caso, del 7 de octubre (fuera del periodo
medido): BOE-B-2026-32590, «suspensión de subasta pública» de una vivienda de la TGSS en Lebrija.
Se había guardado como anuncio nuevo pendiente de extraer, lo que habría duplicado el lote. Ahora
queda enlazado con el anuncio original del 14 de septiembre (BOE-B-2026-29815), que se guarda
también.

## Límites
- Una muestra de tres semanas. El filtro sigue siendo de títulos: una subasta de inmuebles cuyo
  título no nombre ningún bien seguirá fuera.
- «Bienes patrimoniales» puede incluir otros bienes (el de Valencia incluye uno de un abintestato).
  La extracción por lotes decide el tipo de cada uno.
