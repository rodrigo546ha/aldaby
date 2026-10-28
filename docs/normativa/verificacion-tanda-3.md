# Verificación de la tanda 3: regulación del alquiler (F2.4)

**Cargadas:** 2026-10-28 · **Estado:** todas con `verified: false` · **Revisa:** Rodrigo
**Fichero:** `services/api/data/rules/alquiler.yaml`

Son reglas cualitativas: no dan cifras, sino si un tipo de alquiler se puede ejercer, en qué
régimen y con qué requisitos. Los requisitos estatales, autonómicos y municipales se suman.

## 1. Zonas tensionadas en la Comunidad de Madrid · `madrid-zonas-tensionadas`

- **Cargada:** ninguna zona declarada (`declared: false`), revisado hasta la resolución del
  segundo trimestre de 2026 ([BOE-A-2026-16532](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532)).
- **Cómo lo comprobé:** busqué en el BOE todas las resoluciones del Ministerio con «zonas de mercado
  residencial tensionado» en el título (diez y una corrección, de marzo de 2024 a julio de 2026). En
  todas, «Madrid» solo aparece en la firma («Madrid, 24 de julio de 2026.–El Secretario de Estado…»).
- [ ] Que ninguna resolución incluye municipios de la Comunidad de Madrid.
- [ ] **Pendiente cada trimestre:** la resolución del tercer trimestre de 2026 debería salir a finales
      de octubre. Al revisarla, actualizar `checked_through`.

## 2. Vivienda habitual · `alquiler-habitual-lau` y `alquiler-habitual-rdl-29-2026`

- **Base:** LAU, art. 2, redacción anterior al RDL 29/2026: «necesidad permanente de vivienda».
- **Escenario (RDL 29/2026, pendiente):** art. 2.1 nuevo, que incluye «el arrendamiento parcial de una
  habitación o estancia».
- [ ] Ambos textos. La base la leí en la versión del BOE «publicada el 02/10/2026» (tras derogarse el RDL 26/2026).

## 3. Temporada · `alquiler-temporada-lau` y `alquiler-temporada-rdl-29-2026`

- **Base:** LAU, art. 3.2 anterior: uso distinto del de vivienda, «celebrados por temporada, sea ésta
  de verano o cualquier otra». Requisito: número del Registro Único de Arrendamientos para anunciarlo en
  plataformas ([RD 1312/2024](https://www.boe.es/buscar/act.php?id=BOE-A-2024-26931), efectos desde el 01/07/2025).
- **Escenario (RDL 29/2026):** vivienda temporal (arts. 2.3 y 9 bis): causa justificada de
  desplazamiento, más de 31 días y como regla general no más de 12 meses; si se supera sin causa o se
  encadenan más de dos contratos, pasa a vivienda habitual. El art. 3.2 deja de admitir el alojamiento.
- [ ] Los requisitos de ambos regímenes.
- [ ] **Duda abierta:** el RD 1312/2024 define el alquiler de corta duración por remisión al art. 3.2
      de la LAU, que el RDL cambia. ¿Sigue exigiéndose el número de registro a la vivienda temporal?

## 4. Habitaciones · `alquiler-habitaciones-lau` y `alquiler-habitaciones-rdl-29-2026`

- **Base:** la LAU anterior no las regula expresamente. Lo he dejado como «régimen por confirmar en la
  consulta legal (F0.6)», sin requisitos.
- **Escenario (RDL 29/2026):** vivienda habitual, con plazo mínimo y prórrogas.
- [ ] El tratamiento de la base: llévalo a la consulta legal.

## 5. Uso turístico · tres niveles

- **Estatal** (`alquiler-turistico-estatal`, desde el 01/07/2025):
  - Aprobación expresa y previa de la comunidad: 3/5 de propietarios que representen 3/5 de las cuotas
    ([LPH, arts. 7.3 y 17.12](https://www.boe.es/buscar/act.php?id=BOE-A-1960-10906), con efectos del 03/04/2025).
  - Número del Registro Único de Arrendamientos.
- **Comunidad de Madrid** (`madrid-alquiler-turistico`): declaración responsable, CIVUT, certificado y
  aprobación de la comunidad, seguro de responsabilidad civil, vivienda completa, capacidad máxima.
  Tomado de la [sede electrónica](https://sede.comunidad.madrid/comunicaciones-declaraciones/vivienda-uso-turistico).
- **Municipio de Madrid** (`madrid-capital-alquiler-turistico`): licencia urbanística de actividad y
  funcionamiento.
- [ ] Los requisitos de los tres niveles.
- [ ] **Fechas:** las reglas autonómica y municipal empiezan el 08/10/2026 (fecha de la sede consultada).
      Falta leer el Decreto 27/2026 en el BOCM para fijar su entrada en vigor.
- [ ] **Plan Reside:** según fuentes secundarias, limita dónde se puede obtener la licencia en Madrid
      capital (en edificios residenciales, solo con acceso independiente fuera del centro). Falta leerlo
      en el BOCM y comprobarlo por dirección (con la sección censal, F3).
- [ ] Que no hace falta modelar el periodo anterior al 01/07/2025.

## Encontrado en el RDL 29/2026 y no cargado

- **Art. 1:** hasta el 31/12/2030 limita comprar viviendas por menos del 70 % de su valor de mercado a
  las entidades dedicadas a comprar por debajo de tasación y a las personas jurídicas grandes tenedoras.
  No afecta a un inversor particular, pero sí puede afectar a clientes profesionales (F7) y al canal de
  subastas (F4). Pendiente de convalidación.
- **Arts. 7, 8 y 10:** cambios en el IVA, en la Ley de Haciendas Locales y en la plusvalía municipal.
  Revisar al cargar las reglas de venta (inventario, filas 3.x) y de compra de vivienda nueva.
