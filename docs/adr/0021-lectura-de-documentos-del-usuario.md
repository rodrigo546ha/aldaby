# ADR-0021: Lectura de documentos del usuario con OCR local y sin guardar el documento

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.3

## Contexto
F6.3 pide leer la nómina, la declaración de la renta y el extracto bancario del usuario para su
perfil, con confirmación manual. Son los documentos con más datos personales del producto: DNI,
cuentas, empresa y, a veces, categorías especiales (art. 9 del RGPD: cuota sindical, bajas,
asignación a la Iglesia). ADR-0019 ya fijó que solo van al paso que extrae sus campos y que las
categorías especiales no se extraen. La extracción con evidencia (ADR-0013, ADR-0020) exige un
texto contra el que comprobar las citas.

## Decisión
- **Formatos:** PDF con texto (`pypdf`, BSD), PDF escaneado y fotos (las páginas se pasan a imagen
  con `pypdfium2`, Apache 2.0/BSD, y se leen con **Tesseract** en local, Apache 2.0, con el idioma
  español; `pytesseract` como envoltorio) y texto pegado. Una página de PDF sin texto suficiente se
  lee con OCR. Nada sale del equipo o del servidor propio.
- **OCR antes que modelo con visión:** el OCR da un texto y la extracción sigue comprobando que cada
  cita está en él. Un modelo con visión daría valor y cita sin nada contra lo que comprobarlos, y
  puede inventar dígitos. El OCR puede leer mal un número: por eso la confirmación muestra la cita
  y avisa de que el texto sale de un escaneo.
- **El usuario dice qué documento es** (nómina, declaración o extracto); no lo adivina el modelo.
  Cada tipo tiene su esquema de campos con cita (`agent/documents.py`) y se comprueba como en
  ADR-0020: la cita tiene que estar en el texto del documento y el número, en la cita.
- **Qué se saca de cada uno** (y a qué campo del perfil va):
  - *Nómina:* líquido a percibir y si las pagas extra van prorrateadas → ingresos netos al mes. Sin
    prorrata, se supone que hay catorce pagas y la nota lo dice para que el usuario lo corrija.
  - *Declaración (modelo 100):* base liquidable general y del ahorro sometidas a gravamen y años de
    nacimiento de los descendientes → `taxable_base`, `savings_base` y `descendant_birth_years`. Se
    buscan por su nombre, no por el número de casilla, que cambia de un año a otro. El tipo
    marginal no se toma del documento: lo calcula el motor del IRPF (ADR-0007).
  - *Extracto:* saldo final y cuotas de préstamos o hipotecas → ahorro disponible (como propuesta:
    el saldo no es lo que el usuario dedicaría) y cuotas mensuales (una por concepto).
- **El documento no se guarda:** se lee en memoria, se extraen los campos y se descarta. En la
  entrevista cifrada (ADR-0020) quedan solo los campos con su cita y una línea por documento (tipo,
  cómo se leyó y cuántos datos dio). En las citas guardadas se tapan los IBAN y los DNI o NIE.
- **Categorías especiales:** los esquemas no tienen campos para ellas, y las instrucciones dicen
  que no se copien en ninguna cita.
- **Límites:** hasta 10 MB y 10 páginas por documento; el texto que va al modelo se corta a la
  ventana de contexto y se avisa.
- **Subida en JSON con el fichero en base64:** sin añadir `python-multipart`.

## Prueba con qwen3:14b (2026-10-31)
Con tres documentos sintéticos (nómina en PDF con DNI, cuota sindical y una línea de incapacidad
temporal; declaración en foto leída con OCR; extracto con IBAN y cuotas), la declaración salió
entera y bien por OCR (bases, ejercicio y descendientes), las cuotas del extracto también, y no se
extrajo ninguna categoría especial ni el DNI. Dos fallos del modelo, corregidos en código:
- **No vio la línea «Prorrata pagas extraordinarias»** y la nómina salió a × 14 / 12: 2.663,91 € al
  mes en lugar de 2.283,35 €, un 16 % de más. Ahora una línea del documento que dice «prorrata…
  pagas» basta para darla por prorrateada.
- **No leyó «Saldo final a 31/10/2026 24.557,80».** Si el modelo no da un importe, se toma el último
  importe con formato de euros de la línea con la etiqueta, más estricta que la de la comprobación
  («saldo final», no «saldo anterior»; «líquido», no «neto»). El valor sigue saliendo del
  documento.

## Opciones consideradas
- **Modelo con visión** (granite3.2-vision): entiende mejor la maquetación, pero la cita deja de
  garantizar nada. Descartada.
- **Solo PDF con texto:** sin instalar nada en el sistema, pero los escaneos y las fotos son
  habituales. Descartada por decisión de Rodrigo.
- **Guardar el documento cifrado:** permitiría revisarlo después, pero guarda mucho más de lo que
  el plan necesita. Descartada.

## Consecuencias
- Dependencias nuevas: `pypdf`, `pypdfium2`, `pytesseract` (y Pillow por ellas) y el binario
  `tesseract` con el idioma español en el sistema (`brew install tesseract tesseract-lang`; en el
  servidor de F7, el paquete de la distribución). Solo `documents/` las importa.
- Sin el binario, los PDF con texto y el texto pegado siguen funcionando; un escaneo responde que
  falta el OCR.
- Las pruebas usan documentos sintéticos generados en el test; los reales, si los hay, van en
  `tests/fixtures/private/` (fuera de git).
