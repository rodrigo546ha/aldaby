# Fuentes de oferta que podemos usar, por nivel de permiso

Pregunta de Rodrigo (2026-11-02): qué fuentes de oferta, aparte de Solvia, sabemos que podemos usar,
cubriendo la mayor parte posible del mercado, con prioridad en los pisos.

**Método.** Cuatro investigaciones en paralelo, una por grupo de fuentes, todas de solo lectura
(sin formularios, sin cuentas y sin descargar anuncios). Cada una tiene su detalle, con citas y URL,
en `fuentes-2026-11/`:
- `publicas.md`
- `agencias-y-crm.md`
- `portales-y-datos.md`
- `bancos-servicers-subastas.md`

Lo marcado **(comprobado)** lo he vuelto a leer yo en la fuente el mismo día. Lo demás conserva la
marca de cada informe: «(leído)» o «(sin verificar)». Reglas que aplican:
- regla de oro 3: sin scraping de webs que lo prohíben, y cada canal nuevo lleva su ADR;
- regla de oro 7: la comisión no toca la recomendación.

**Niveles:**
- **A:** se puede usar ya. Hay licencia que permite la reutilización comercial y el `robots.txt` no
  lo impide.
- **B:** basta un alta o una confirmación estándar, sin negociar.
- **C:** requiere un acuerdo.
- **D:** no.

## Respuesta corta

1. **Lo que podemos usar ya cubre poco mercado.** Son subastas y ventas del sector público:
   - el BOE, que ya usamos;
   - el **Patrimonio del Estado**;
   - el **INVIED**.

   A eso se suman los enlaces que pega el usuario y el **feed XML de una agencia que nos lo ceda**.
   Ninguna fuente de volumen de pisos es A.
2. **La oferta de pisos está en agencias y portales.** Sin su permiso no se puede usar ninguna.
   - Ningún portal publica una licencia que lo permita.
   - Ningún CRM publica una cuota de mercado con fuente, ni hay una cifra fiable del reparto de la
     oferta por canal. No la invento.
3. **Las tres vías con volumen**, por orden de control nuestro:
   1. **El feed XML de cada agencia, con su permiso.** Escala con los clientes profesionales y no
      depende de ningún portal.
   2. **La Search API de idealista.** Es una solicitud estándar (formulario ya rellenado), pero
      idealista es un proveedor comercial, así que necesita tu decisión y un ADR.
   3. **Acuerdos con los servicers que no son de Intrum:** Servihabitat, Aliseda (con
      Anticipa y parte de Sareb), Altamira, Hipoges (con parte de Sareb) y Diglo. Ya tienen correo.

## Aviso: dejar fuera a Solvia deja fuera a todo Intrum

- **Solvia, Haya y Casaktua son el mismo grupo, Intrum.** La web de Intrum lo dice así (comprobado):
  «Solvia.es y Casaktua.com los portales inmobiliarios de Intrum».
- **CaixaBank** eligió en 2023 a «Solvia-Intrum» para vender sus inmuebles (comprobado, nota de
  CaixaBank). La misma nota dice que, tras comprar Haya, Solvia-Intrum sería su único servicer de
  venta. El contrato era a tres años, así que conviene confirmar si sigue vigente.
- **Ibercaja** vende «de la mano de Ibercaja y Solvia» (leído).
- **BBVA** vendería hoy también por Solvia (sin verificar).

Excluir a Solvia significa, por tanto, renunciar a la cartera de venta de esos bancos. El correo
rebotó porque el buzón no existe, no porque nos rechazaran: la vía sigue abierta por teléfono
(911 751 195).

## Nivel A: se puede usar ya

| Fuente | Qué aporta | Por qué es A | Qué falta |
| --- | --- | --- | --- |
| BOE: sumario, sección V y avisos de subastas judiciales | Anuncios y subastas públicas | Ya en uso, con `txt.php` y `robots.txt` respetado | Ampliar los avisos de la sección IV a toda España |
| **Patrimonio del Estado** | Subastas, concursos, ventas directas y abintestatos del Estado en toda España. El 2026-11-02 su RSS de subastas tenía 8 procedimientos (comprobado) | El aviso legal de Hacienda permite «la reutilización de los documentos sometidos a ellas para fines comerciales y no comerciales» (comprobado). El `robots.txt` solo bloquea `/RRHH/` y PDF concretos (comprobado) | ADR y canal: tres RSS (subastas `hiloId=12`, ventas directas `15`, abintestatos `13`) y los lotes, que vienen en el pliego en PDF. Citar «Origen de los datos: Ministerio de Hacienda» |
| **INVIED (Defensa)** | Viviendas, locales y solares desafectados | Misma cláusula de reutilización (comprobado). Su aviso legal también tiene una prohibición general, así que conviene un correo que lo aclare | Hoy no hay ninguna subasta: el RSS está vacío (comprobado). Canal pequeño, para cuando haya oferta |
| Enlace o texto pegado por el usuario | Cualquier anuncio | ADR-0015 | Ya en uso |
| **Feed XML de una agencia** (formato Kyero v3) | La cartera entera de esa agencia | Lo genera la agencia en su CRM y lo comparte. Witei lo documenta así (comprobado): «Share this link with your external website or portal» | Consentimiento escrito de la agencia en el alta (F7), ADR y canal `feed_agencia` |

## Nivel B: basta una solicitud estándar

| Fuente | Qué aporta | Qué pedir |
| --- | --- | --- |
| **idealista, Search API** | El portal con más pisos. Única API oficial de lectura | No publica precio, límites, atribución ni almacenamiento. Formulario rellenado en aldaby.admin@gmail.com; envío pendiente de tu decisión (regla de oro 3) |
| **Plataforma de Contratación del Sector Público (PLACSP)** | Enajenaciones de ayuntamientos y organismos. Es la única fuente pública nueva con volumen posible | La licencia permite la reutilización comercial (leído), pero el `robots.txt` es `Disallow: /` en el host de los datos (comprobado). Pedir confirmación por escrito y comprobar en un ZIP mensual si de verdad hay inmuebles |
| Seguridad Social (TGSS) | Venta de inmuebles propios y subastas de embargos | La licencia permite la reutilización comercial (leído). Solo hay aplicación web: pedir un fichero o un permiso de consulta automatizada |
| BOP de Barcelona | 8 RSS de «Dades obertes» | No declaran licencia. Preguntar a la Diputación de Barcelona cuál es |

## Nivel C: hace falta un acuerdo

| Grupo | Fuentes y contacto | Nota |
| --- | --- | --- |
| Servicers | Servihabitat, Aliseda, Hipoges, Altamira (914 842 874), Diglo (910 150 732) | Correos ya preparados, salvo Altamira y Diglo (teléfono). Sareb vende por Aliseda e Hipoges, y quizá por Servihabitat (sin verificar) |
| Bancos con portal propio | **Abanca, EscogeCasa:** info@escogecasa.es, 981 981 250. Tiene «Inversores» y «Acceso colaboradores». **Unicaja Inmuebles:** solo formulario. **Bankinter:** 901 888 050. **Caja Rural Central:** teatendemos@crcentral.es. **Banca March** y **Cajamar:** correos ya preparados | Pequeños, pero tratan directamente, sin servicer. EscogeCasa es la puerta más clara |
| CRM de agencias | **Sooprema** (correo ya preparado). **eGO Real Estate:** formulario, «Tell us which one!». **Inmobalia:** API y red de 410 agencias. **Kyero:** preguntar si leer su formato requiere permiso | Inmovilla es de idealista; Witei e Inmoweb, de Adevinta. No tienen interés en un destino nuevo, pero el feed XML de Witei lo controla la agencia (nivel A) |
| Portales | **Redpiso:** su `robots.txt` deja abierto `/api/properties`, pero no hay términos; preguntar en info@redpiso.es (correo ya preparado). Housfy. Nestoria (API antigua, no se sabe si sigue activa) | Un `Allow` en el `robots.txt` no es una licencia |
| Datos comerciales | **Brains RE** (sales@brainsre.com): oferta de todos los portales por FTP o API. **idealista/data** | Proveedor comercial: tu decisión y un ADR. Preguntar si incluye enlace a la ficha y si se puede mostrar a los usuarios |
| Subastas privadas | **Surus/Escrapalia** (info@surusin.com: activos de concursos). **Diario de Subastas** (info@diariodesubastas.com: agregador, preguntar por `api.diariodesubastas.com`). eActivos | No son pisos de banco, sino liquidaciones |
| Públicas | ADIF, BOCM, BOJA, BOP de Valencia y de Sevilla | Sus avisos prohíben el uso comercial sin autorización |

## Nivel D: no

- **Intrum** (Solvia, Haya y Casaktua) y lo que vende por ellos: CaixaBank e Ibercaja.
- **Portales:** Fotocasa, habitaclia, pisos.com, yaencontre, Trovit/Mitula (sus feeds son de
  entrada), Milanuncios, Kyero como fuente, thinkSPAIN, spainhouses, Indomio, Century 21, RE/MAX,
  Engel & Völkers, Tecnocasa y Donpiso (sus términos no se pudieron leer).
- **Sareb directa** (su web bloquea).
- **Registro Público Concursal** (prohíbe la «robotización»).
- **DOGC y SUMA** (`Disallow: /`).
- **BidX1** (ya no opera en España).
- **Kutxabank y Deutsche Bank** (sin portal propio).

## Hallazgo lateral: un dato público para el plan

El CSV «Subastas judiciales» del Ministerio de Justicia en datos.gob.es tiene una licencia que
permite la reutilización comercial (leído) y cubre las subastas del Portal del BOE desde 2021.

- Trae el importe de subasta, la tasación y el estado.
- No trae dirección, así que no es oferta.
- Sirve para estimar el descuento entre la tasación y la subasta como parámetro del plan, marcado
  `PROVISIONAL` hasta leerlo entero.

## Correcciones a los documentos anteriores

- **Haya y Casaktua** no son canales distintos: son Intrum, igual que Solvia. El error de
  certificado de casaktua.com se debe a que usa el de `solvia.es`.
- **anticipa.es** es una empresa de software de Málaga, no Anticipa Real Estate. Anticipa vende por
  Aliseda.
- **SEPES** es hoy Casa 47 y se dedica al alquiler asequible, no a la venta (sin verificar).

## Orden propuesto

1. **Aquí, en código, primero:**
   - el canal de feeds XML de agencias (formato Kyero v3), con su ADR;
   - el canal del Patrimonio del Estado (RSS y pliego en PDF), con su ADR.

   Son las dos únicas vías A que faltan, y el feed de agencias es la palanca de volumen que depende
   de nosotros.
2. **Tu decisión:** la Search API de idealista (y, si se quiere, Brains RE o idealista/data). Los
   tres son proveedores comerciales.
3. **Correos nuevos** a:
   - Abanca/EscogeCasa;
   - Redpiso, con la pregunta sobre `/api/properties` añadida al borrador que ya existe;
   - eGO, Inmobalia y Kyero;
   - PLACSP (por el `robots.txt`);
   - la Diputación de Barcelona (por la licencia);
   - TGSS;
   - Surus y Diario de Subastas;
   - Caja Rural Central.

   Llamadas: Bankinter, Altamira y Diglo, y Solvia si se recupera.
4. **Antes de la beta:** la consulta legal (F0.6). Tiene que cubrir el consentimiento del
   propietario cuando la agencia nos cede el anuncio y los derechos de las fotos.
