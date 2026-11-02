# Proceso para conseguir acceso a las fuentes de oferta

Para Rodrigo: qué hacer con cada fuente, en qué orden y con quién hablar. Los contactos están
copiados de cada web, con la fecha en que se leyeron (2026-11-02); ninguno está inventado. Si pone
«no aparece», hay que buscarlo por otra vía: LinkedIn, una presentación o una llamada.

Detalle de cada fuente: `f4-5-servicers.md` (servicers) y `fuentes-de-oferta-vivienda.md` (el
resto).
Qué se puede usar ya y qué no, por nivel de permiso: `fuentes-utilizables.md` (2026-11-02).

Reglas que valen para todas (`CLAUDE.md`):
- Sin permiso escrito, no se automatiza nada en una web que lo prohíbe (regla de oro 3). Cada
  canal nuevo lleva su ADR.
- Si hay comisión, se declara y no toca la recomendación (regla de oro 7, ADR-0036).

## Pasos comunes a cada fuente privada
1. **Contacto.** Correo con el borrador que toque (`borrador-correo-servicers.md`, que vale
   también para bancos y portales cambiando el nombre), o el formulario o teléfono que dé la web.
   Mejor si alguien te presenta.
2. **Primera llamada.** Qué datos tienen (tipo, dirección o referencia catastral, superficie,
   precio, ocupación, fotos), en qué formato (feed XML, API, fichero), con qué frecuencia, y si
   piden comisión, exclusividad o condiciones de marca.
3. **Condiciones por escrito.** Uso permitido (analizar y mostrar a nuestros usuarios), cita y
   enlace, conservación de los datos, baja de una oferta vendida, datos personales (ninguno, salvo
   el contacto comercial), duración y cancelación.
4. **Revisión legal.** La consulta legal de F0.6 revisa el acuerdo antes de firmarlo.
5. **ADR del canal** (`docs/adr/`): formato, frecuencia, condiciones, qué se guarda y qué no.
6. **Canal** en `offers/channels/`, con fixtures reales de lo que manden y un trabajo programado
   en la cola.

## 1. Lo que hay que arreglar en lo que ya tenemos
| Qué | Por qué | Siguiente paso |
| --- | --- | --- |
| Canales del BOE (`boe_seccion_v`, `boe_subastas_judiciales`) | Descargaban cada anuncio de `/diario_boe/xml.php?id=…`, que el `robots.txt` del BOE prohíbe (`Disallow: /diario_boe/xml.php?`) | **Hecho (2026-11-02):** leen `txt.php` y se saltan los documentos que el `robots.txt` prohíbe |
| Enlace pegado (F4.1) en dominios que prohíben enlazar o reutilizar | Solvia, Servihabitat, Aliseda, Diglo, Fotocasa | Consulta legal (F0.6); mientras tanto, pedir el texto |

## 2. Públicas
| Fuente | Contacto | Qué pedir |
| --- | --- | --- |
| **Portal de Subastas del BOE** (judiciales, AEAT, Seguridad Social, notariales) | Solo por formulario: https://www.boe.es/contactar/formulario_simple.php?tipo=SUB | `borrador-correo-aeboe-subastas.md` |
| **BOE, sumario y sección IV** | Abiertos (API de datos abiertos) | Ampliar los avisos de subastas judiciales a toda España (código, aquí) |
| **Seguridad Social, subastas** | C/ Astros 5 y 7, 28007 Madrid; 915 038 756 / 915 038 464. Correo: no aparece | Si hay fichero o RSS de sus subastas |
| **INVIED (Defensa)** | inviedbuzon@oc.mde.es; 900 210 425 | Aviso de nuevas subastas (hoy no hay ninguna en curso) |
| **Patrimonio del Estado** | Correo: no aparece; tiene RSS de subastas y concursos | Leer su RSS (reutilización permitida con cita; comprobar su `robots.txt` antes) |

## 3. Portales
| Portal | Contacto | Qué pedir |
| --- | --- | --- |
| **idealista** | Formulario: https://developers.idealista.com/access-request | Clave de la Search API: precio, límites y condiciones. **Antes, tu decisión:** es un proveedor comercial de datos (regla de oro 3) |
| **Fotocasa / habitaclia** (Adevinta) | ayuda@fotocasa.pro | Si dan acceso a terceros a su cartera |
| **Trovit / Mitula** (Lifull Connect) | https://www.lifullconnect.com/contact-us/ | Lo mismo |
| **pisos.com, yaencontre** | No aparece | Buscar contacto comercial |
| **Redes de franquicias** (RE/MAX, Engel & Völkers, Redpiso, Century 21, Tecnocasa) | remax@remax.es; spain@engelvoelkers.com; info@redpiso.es; Century 21 y Tecnocasa: no aparece | Feed de su cartera |

## 4. Servicers
| Servicer | Contacto |
| --- | --- |
| Solvia | web@solvia.es **rebota** (2026-11-02: «550 5.4.1 Recipient address rejected», el buzón no existe aunque lo cite su aviso legal). Teléfono 911 751 195; alta de prescriptor: https://www.solvia.es/es/login-profesional |
| Servihabitat | servihabitat@servihabitat.com; inversores: https://inversores.servihabitat.com/es/ |
| Aliseda (con Anticipa y activos de Sareb) | clientes@alisedainmobiliaria.com; 91 187 66 74 |
| Altamira (doValue) | Formulario: https://www.altamirainmuebles.com/profesionales; 914 842 874 |
| Hipoges | inversores.es@hipoges.com; subastas.re@hipoges.com |
| Diglo (Santander) | 910 150 732 (inversores); 91 157 44 02 (comercial). Correo: no aparece |
| Haya, Casaktua | Son Intrum, como Solvia (`fuentes-utilizables.md`) |
| Sareb | No vende directamente: por Aliseda e Hipoges, y quizá por Servihabitat (sin verificar) |

## 5. Bancos con portal propio
| Banco | Contacto |
| --- | --- |
| Banca March | info@bancamarch.es; 900 227 227 |
| Cajamar | cajamar@grupocooperativocajamar.es; +34 950 21 01 91 |
| CaixaBank (Building Center), Bankinter, Ibercaja, Unicaja, Kutxabank, Abanca, Caja Rural | No aparece o no comprobado |

## 6. Agencias (clientes profesionales)
La agencia es dueña de su cartera y puede dárnosla. Proceso:
1. En el alta del cliente profesional (F7), la agencia acepta por escrito que HouseFinder lea su
   cartera para analizarla.
2. La agencia activa en su CRM la exportación XML con el formato de Kyero (Witei, Inmovilla y
   otros la tienen) y nos da el enlace.
3. Para los CRM con API (Sooprema: estate@sooprema.com; Inmovilla: 966 673 149; Inmoweb:
   comercial@inmoweb.es), pedir al CRM el alta como destino o integración.
4. Un canal `feed_agencia` que lee XML Kyero v3, con su ADR.

## Orden recomendado
1. **Esta semana:**
   - Formulario a la AEBOE (Portal de Subastas).
   - Correos a los seis servicers, a Banca March y a Cajamar.
   - Decidir qué hacemos con `xml.php`.
2. **Decisión tuya:** si pedimos la API de idealista (proveedor comercial).
3. **Aquí, en paralelo:** ampliar los avisos de subastas judiciales a toda España y preparar el
   canal de feeds XML de agencias (ADR primero).
4. **Antes de la beta (enero de 2027):** la consulta legal (F0.6), con las preguntas de los
   enlaces pegados y de los acuerdos.
