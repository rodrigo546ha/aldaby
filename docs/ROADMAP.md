# Roadmap de HouseFinder

**Fase activa:** F0 (validación, sin código) en paralelo con F1 (motor financiero).
**Hito principal:** beta privada con 3–5 profesionales a mediados de enero de 2027.
**Decisión de continuar:** finales de marzo de 2027, según los criterios de F9.

Las fechas suponen una dedicación parcial (tardes y fines de semana) y empiezan la semana del
2 de noviembre de 2026. Son orientativas: lo que manda es el criterio de salida de cada fase.

## Resumen

| Fase | Qué se consigue | Semanas | Fechas orientativas |
| --- | --- | --- | --- |
| F0 | Validar que el plan genera confianza, sin código | 1–3 | 2–22 nov |
| F1 | Motor financiero: hipoteca, capacidad, cash flow, estrés | 1–4 | 2–29 nov |
| F2 | Motor de normativa y fiscalidad con reglas verificadas | 4–6 | 23 nov–13 dic |
| F3 | Datos territoriales: secciones censales, renta, demografía | 5–7 | 30 nov–20 dic |
| F4 | Ingesta de oferta: enlaces, BOE y servicers | 7–9 | 14 dic–3 ene |
| F5 | Valoración: renta y precio estimados con rango | 8–10 | 21 dic–10 ene |
| F6 | Agente y plan de inversión completo (web y PDF) | 9–11 | 28 dic–17 ene |
| F7 | Beta privada con profesionales | 11–15 | 11 ene–14 feb |
| F8 | Pase de compra para particulares en Madrid | 14–17 | 1–28 feb |
| F9 | Medir y decidir | 18–21 | 1–31 mar |

Dependencias: F1 → F2 → F6; F3 → F4 (geocodificación) → F5 → F6; F6 → F7 → F8. F0 informa a todas.

Cómo pedir trabajo a Claude Code: «Trabaja en la tarea F1.5 del roadmap», «Termina F2 y comprueba su
criterio de salida». Al cerrar una tarea, marcarla `[x]` en este archivo.

---

## F0 · Validación (sin código)

**Objetivo.** Comprobar con personas reales que un plan de inversión personal genera confianza y
acción, antes de invertir meses en construirlo.

**Tareas**

- [ ] F0.1 Preparar la plantilla de plan manual (`docs/templates/plan-manual.md`) en hoja de cálculo.
- [ ] F0.2 Conseguir 10 personas que estén pensando invertir (red propia, foros, LinkedIn).
- [ ] F0.3 Hacer 10 planes a mano con datos públicos y anotar cuánto tiempo lleva cada uno.
- [ ] F0.4 20 entrevistas (`docs/templates/entrevista.md`): 12 inversores y 8 profesionales
      (intermediarios hipotecarios, asesores, agencias).
- [ ] F0.5 Probar Invisor y Cassandra AI con 3 perfiles tipo y anotar qué preguntas dejan sin responder.
- [ ] F0.6 Consulta legal: scraping y reutilización de datos, intermediación hipotecaria (Ley 5/2019),
      RGPD de datos financieros, avisos legales del plan.
- [ ] F0.7 Elegir los 3–5 profesionales candidatos al piloto de F7 y pedirles compromiso.

**Entregables.** 10 planes, notas de 20 entrevistas, informe legal, lista de pilotos.

**Criterio de salida.** Al menos 5 de 10 planes llevan a una acción (visita, preaprobación u oferta)
y al menos 3 profesionales se comprometen al piloto. Si no se cumple: revisar propuesta antes de F6.

---

## F1 · Motor financiero

**Objetivo.** Calcular con exactitud y trazabilidad todo lo que depende del dinero del usuario.

**Tareas**

- [x] F1.0 Contrato `Figure` v2 (ADR-0004): clave estable, fuentes tipadas (`SourceRef`), rango
      opcional y marca `PROVISIONAL` propagada; porcentajes en tanto por uno; test de dirección
      de dependencias entre módulos.
- [x] F1.1 Cuota por sistema francés y cuadro de amortización (`engines/mortgage.py`).
- [x] F1.2 Capacidad de compra por ahorro e ingresos, con plazo limitado por edad.
- [x] F1.3 Cuota en escenario de estrés de tipos.
- [x] F1.4 Cash flow, rentabilidad bruta, dinero aportado y cash-on-cash (`engines/cashflow.py`).
- [x] F1.5a Criterios bancarios como datos con fecha (`ParamBook`, ADR-0005), sin valores por
      defecto en el código.
- [ ] F1.5 Calibrar `BankCriteria` (LTV, ratio de endeudamiento, edad máxima) con 2–3 bancos o un
      intermediario; documentar la fuente y quitar la marca `PROVISIONAL`.
- [x] F1.6 Hipoteca mixta y comparación fija / variable / mixta: coste total esperado y peor cuota.
- [x] F1.7 Trayectoria esperada del Euríbor a partir de la curva publicada (Banco de España / BCE),
      como datos con fecha, no como predicción propia.
- [x] F1.8 Plazo recomendado: el mínimo que mantiene el cash flow positivo en el escenario de estrés.
- [x] F1.9 TIR a 10 años con escenarios de revalorización (que llegarán de F5) como parámetro.
- [x] F1.10 Endpoint `POST /simulate/investment` y página web del simulador de capacidad.

**Criterio de salida.** Todos los cálculos con test de valor conocido, cifras como `Figure`, y un
plan manual de F0 reproducido por el motor con diferencias menores de 1 €.
*Estado:* el arnés de la prueba de oro está listo (`tests/test_golden_plans.py`) y pasa con un plan
sintético; falta un plan real de F0 (F0.3) para dar el criterio por cumplido.

---

## F2 · Normativa y fiscalidad

**Objetivo.** Que cada regla legal que afecta a la rentabilidad esté en datos, verificada y con fecha.

**Tareas**

- [x] F2.1 Motor `RuleBook`: territorio jerárquico, vigencia, estado y verificación.
- [x] F2.1a Catálogo de tipos de regla con esquema de parámetros y validador de reglas
      (`make rules-check`, también en CI): territorios, vigencias solapadas y revisor obligatorio.
- [x] F2.2 Inventario de reglas necesarias para Madrid: impuesto de compra (segunda mano y obra
      nueva), gastos de notaría y registro, IBI orientativo, reducción del rendimiento del alquiler,
      amortización fiscal, mínimos de IRPF relevantes.
- [ ] F2.3 Cargar cada regla desde la fuente oficial con `verified: true` tras revisión.
      *Estado:* cargadas sin verificar las tandas 1 a 5 (`docs/normativa/verificacion-tanda-*.md`);
      falta la revisión de Rodrigo y las filas pendientes del inventario (2.8, 3.2, ascendientes).
- [x] F2.4 Normativa de alquiler: zonas tensionadas (lista oficial), alquiler de temporada, por
      habitaciones y turístico (mayoría de 3/5 de la comunidad, registro autonómico).
- [x] F2.5 Escenarios: reglas `pendiente_convalidacion` y comparación «con / sin» en el plan.
- [x] F2.6 Monitor del BOE y del BOCM: detectar disposiciones nuevas sobre vivienda y abrir una
      tarea de revisión (la IA resume, una persona decide). Trabajos `watch_boe` y `watch_bocm`,
      filtros en `data/watch/vigilancia.yaml`, tareas en `review_tasks` y
      `python -m housefinder.watch tareas`. El resumen de la IA llega con `LLMClient` (G5).
- [x] F2.7 Conectar `TaxParams` del motor de cash flow con `RuleBook`, citando `rule_ids`.
- [x] F2.7a Cuota incremental del IRPF (ADR-0007): escalas estatal y autonómica, mínimos,
      límite de intereses y reparación con arrastre a cuatro años, también en la TIR.

**Criterio de salida.** Un plan de Madrid sale con todas sus reglas citadas y verificadas, y cambiar
una ley solo requiere añadir una regla en YAML.

---

## F3 · Datos territoriales

**Objetivo.** Conocer cada zona por sección censal: quién vive, cuánto gana, cómo evoluciona.

**Tareas**

- [x] F3.1 Base de datos local con `make db` y migraciones con ejecutor propio (ADR-0008): `0001_init`,
      `0002` (secciones por cartografía, organizaciones, reproducibilidad del plan).
- [x] F3.2 Cargar la cartografía de secciones censales del INE para la Comunidad de Madrid
      (`make sections`: 4.518 secciones de 2025, 179 municipios).
- [x] F3.3 Cargar el Atlas de Distribución de Renta de los Hogares (INE) por sección
      (`make adrh`: renta y demografía 2015–2024 de Madrid, cada año sobre su seccionado t+1;
      cartografías 2016–2025 cargadas).
- [ ] F3.4 Cargar el padrón (población, edad, nacionalidad) y su evolución.
      *Estado:* los indicadores demográficos del ADRH ya dan población, edad media, menores,
      mayores y % de población española por sección de 2015 a 2024; falta decidir si hace falta
      además el padrón continuo.
- [ ] F3.5 Indicadores de demanda: universidades y matrícula, hospitales y grandes empleadores,
      afiliación a la Seguridad Social por municipio.
- [x] F3.6 Geocodificación con CartoCiudad y asignación de sección censal a una dirección
      (ADR-0009): `GET /territory?address=…` o `?lon=…&lat=…`, con caché y tendencia a 5 años solo
      si la sección conserva el polígono (92 % de las secciones de 2025).
- [ ] F3.7 Registro de cada carga en `sources` (url, licencia, fecha).
      *Estado:* se registran la cartografía, el Atlas de renta y el geocodificador; falta en
      cada cargador nuevo.

**Criterio de salida.** Dada una dirección de Madrid, la API devuelve su sección censal con renta,
población y tendencias, cada valor con su fuente.
*Estado:* cumplido con `GET /territory` (renta, población y demografía 2015–2024, cada cifra con su
fuente); quedan las tareas F3.4 (padrón) y F3.5 (indicadores de demanda).

---

## F4 · Ingesta de oferta

**Objetivo.** Tener oferta real que analizar por tres canales legales.

**Tareas**

- [x] F4.1 Enlace pegado por el usuario: descargar la página que el usuario aporta, extraer los datos
      con el agente (precio, superficie, planta, estado, fotos) y pedir confirmación al usuario.
      *Hecho (ADR-0015):* una descarga a petición suya con `robots.txt` respetado, sin esquivar
      bloqueos y con veto a la red interna; si no se puede, el usuario pega el texto. Extracción en
      la cola (`extract_link`) con citas comprobadas y página `/ofertas` para confirmar o corregir
      cada dato. De las fotos solo se guardan las URL `og:image`, sin descargarlas ni mostrarlas.
      *Pendiente:* la consulta legal (F0.6) y la autenticación (G8; hoy, organización local).
- [x] F4.2 Verificar la API de datos abiertos del BOE con un sumario real y guardarlo como fixture;
      ajustar `ingestion/boe.py` a su esquema (hecho con F2.6: `tests/fixtures/boe/`).
- [ ] F4.3 Subastas del Portal de Subastas del BOE para la provincia de Madrid (revisar condiciones
      de uso; si no hay vía de datos abiertos, ADR antes de implementar).
      *Estado (ADR-0017):* el Portal prohíbe el acceso automático (`robots.txt`: `Disallow: /`) y no
      se lee. El canal `boe_subastas_judiciales` guarda los avisos de la sección IV del BOE de
      juzgados de Madrid (≈ 13 a la semana) con su enlace; el usuario abre el Portal y pega el texto
      del lote en `/ofertas`. *Pendiente:* verificar la lista de partidos judiciales
      (`data/offers/subastas_boe.yaml`) y enviar la consulta a la AEBOE
      (`docs/research/borrador-correo-aeboe-subastas.md`). Investigación:
      `docs/research/f4-3-portal-subastas.md`.
- [x] F4.4 Anuncios de la sección V del BOE: Seguridad Social, INVIED, Patrimonio del Estado.
      *Hecho:* el canal `boe_seccion_v` guarda cada día los anuncios enteros y el trabajo
      `extract_offers` extrae sus lotes con evidencia comprobada (ADR-0013), los ubica y los
      deduplica; cada cita tiene que estar en el tramo de su lote (ADR-0014). Las correcciones no
      crean lotes: se enlazan con el anuncio que corrigen por la página o, sin página, por el
      departamento y el número de expediente (`offers/corrections.py`, columna `corrects_id`).
      Las anulaciones, exclusiones y suspensiones de lotes se tratan igual. Página `/anuncios`:
      cada anuncio con su texto, sus lotes (cada dato con su cita, sin confirmar) y sus
      correcciones; `extract_offers` acepta `ids` para extraer anuncios concretos. El filtro de títulos
      acepta el bien antes o después de la venta y «bienes patrimoniales»
      (`docs/research/f4-filtro-seccion-v.md`). Volumen: `docs/research/f4-volumen-boe.md`.
- [ ] F4.5 Servicers (Solvia, Servihabitat, Aliseda, Altamira, Hipoges): revisar términos de uso de
      cada web, ADR por servicer y contacto comercial para acuerdo.
- [x] F4.6 Normalización y deduplicación por referencia catastral y geolocalización: interfaz
      `Channel`, lo recibido siempre guardado con sus versiones, inmueble por referencia catastral o
      a menos de 30 m con superficie a ±5 %, y sección censal asignada. Ubicación por referencia
      catastral (Catastro, ADR-0016) y, si no, por dirección; el punto tiene que caer en la zona
      cargada y en el municipio de la oferta.
- [x] F4.7 Trabajos programados con reintentos y alertas de fallo (ADR-0010): cola en PostgreSQL con
      `SKIP LOCKED`, esperas de 1 minuto a 1 hora, programaciones por intervalo, alertas en el log
      `housefinder.alertas`; `make worker`. Primeros tipos: `ine_sections` e `ine_adrh`.
      Programaciones diarias en `data/jobs/programaciones.yaml` (`make schedules`): sección V y
      avisos de subastas del BOE, vigilancia del BOE y del BOCM y, si el LLM está configurado,
      la extracción de lotes. En desarrollo, el worker queda siempre en marcha con launchd
      (`make worker-install`, `infra/launchd/`) y Ollama como servicio de Homebrew; la base se
      reinicia con Docker. En producción, F7.

**Criterio de salida.** Cada día entran ofertas nuevas de al menos dos canales, sin duplicados, con
sección censal asignada.

---

## F5 · Valoración

**Objetivo.** Estimar renta y precio de cada inmueble con un rango honesto.

**Tareas**

- [x] F5.1 Recopilar referencias de precio: Portal Estadístico del Notariado, valor tasado del
      Ministerio, IPV del INE (revisar términos de reutilización).
- [x] F5.2 Referencias de alquiler: Sistema Estatal de Referencia del Precio del Alquiler e IPVA.
      *Hecho (ADR-0018):* SERPAVI 2011–2024 por sección (`make serpavi`), valor tasado municipal
      (`make valor-tasado`) e IPV del INE (`make ipv`). El Notariado prohíbe el uso comercial: fuera.
      El IPVA del INE es un índice, no niveles de renta: no hace falta por ahora.
      No hay precio de venta público por sección: el precio se estimará desde la renta.
- [x] F5.3 Modelo base de renta por sección, superficie y características, con intervalo P25–P75.
      *Hecho (ADR-0018):* renta €/m² mes de la sección (o distrito, o municipio) del SERPAVI,
      contraída hacia el municipio con k (k = 0 tras el backtesting de F5.6), × superficie;
      rango P25–P75.
      Solo tipología (colectiva o unifamiliar) y superficie: el SERPAVI no da más características.
- [ ] F5.4 Modelo base de precio y margen de negociación respecto al precio pedido.
      *En parte:* precio €/m² desde la renta con la relación precio/renta del municipio
      (valor tasado / renta municipal), llevado al último trimestre con el IPV; supone la misma
      rentabilidad en todo el municipio. El margen de negociación sobre el precio pedido no tiene
      fuente pública. `GET /valuation` y `valuation/service.py`.
      Cada oferta confirmada y ubicada se valora (`GET /offers/{id}/valuation`,
      `valuation/offer.py`): renta, precio y escenarios del inmueble, precio pedido frente al
      estimado con su rango y rentabilidad bruta al precio pedido (renta pedida si es alquiler).
      Se muestra en la ficha de la oferta; no se presenta como margen de negociación.
- [x] F5.5 Escenarios de revalorización (conservador, base, optimista) a partir de factores
      explicables: población, empleo, renta, oferta nueva.
      *Hecho (decisión de Rodrigo, 2026-10-31):* ciclo de la comunidad con los P25/P50/P75 de las
      ventanas del IPV de la duración del horizonte, y la convergencia de la renta municipal
      frente a la provincia como dimensión del escenario (su signo cambia con el ciclo). La renta
      del hogar y la población no explican el crecimiento relativo; empleo y oferta nueva no se
      cargan (docs/research/f5-5-factores-revalorizacion.md). En el simulador, sin revalorización
      el plan usa la base y da la TIR de los otros dos escenarios.
- [x] F5.6 Backtesting: qué habría estimado el modelo con datos de años anteriores.
      *Hecho:* `python -m housefinder.valuation.backtest` (`make backtest`); informe en
      `docs/research/f5-6-backtesting.md`. Renta por sección a un año: 2,08 % de error mediano
      (k = 0, que pasa a ser el parámetro); una renta de dos años se queda corta un 8 % en los
      años recientes. Precio: actualización con el IPV 2,99 %, relación del año anterior 2,64 %.
      La renta se actualiza con el IPC de alquiler: a dos años, del −7,9 % al −4,2 %.

**Criterio de salida.** Error medio de la renta estimada frente a referencias reales por debajo del
umbral fijado en F0, y cada estimación con su rango.

---

## F6 · Agente y plan de inversión

**Objetivo.** Del perfil al plan completo, explicado y exportable.

**Tareas**

- [x] F6.1 Interfaz propia para el LLM, intercambiable por configuración (ADR-0013, adelantada a G5):
      `agent/llm.py` con un servidor propio de modelos abiertos por la API compatible con OpenAI
      (ADR-0014) y cliente falso. Probado con `qwen3:8b` en Ollama local. *Pendiente:* elegir
      servidor virtual y modelo con una prueba sobre anuncios reales.
- [ ] F6.2 Perfilado conversacional que produce un perfil estructurado y validado.
- [ ] F6.3 Lectura de documentos del usuario (nómina, extracto, declaración) con confirmación manual.
- [ ] F6.4 Herramientas del agente: llama a los motores, nunca calcula.
- [ ] F6.5 Búsqueda inversa: puntuación de ofertas según el resultado esperado para el perfil y sus
      restricciones (cash flow mínimo, riesgo, gestión).
- [ ] F6.6 Recomendación de tipo de alquiler y de gestión activa o pasiva según la ubicación.
- [ ] F6.7 Plan completo: capacidad, hipoteca, cash flow, estrés, escenarios legales, argumentos
      para no comprar y hoja de ruta de compra.
- [ ] F6.8 Exportación a PDF con todas las fuentes citadas.
- [ ] F6.9 Evaluaciones automáticas: extracción de anuncios, ausencia de cifras inventadas en el
      texto del agente y coherencia del plan.

**Criterio de salida.** Los 10 planes manuales de F0 se reproducen con la herramienta en menos de
10 minutos cada uno, y ninguna cifra del texto del agente falta en los `Figure` del plan.

---

## F7 · Beta privada con profesionales

**Objetivo.** Que profesionales reales usen la herramienta con sus clientes y paguen.

**Tareas**

- [ ] F7.1 Cuentas, inicio de sesión y separación de datos por cliente.
- [ ] F7.2 Gestión de varios perfiles de cliente por profesional.
- [ ] F7.3 Planes con la marca del profesional.
- [ ] F7.4 Avisos legales y consentimiento de tratamiento de datos.
- [ ] F7.5 Despliegue en AWS con copias de seguridad y monitorización básica.
- [ ] F7.6 Piloto de 4 semanas con 3–5 profesionales y sesión de feedback semanal.
- [ ] F7.7 Propuesta de precio al final del piloto.

**Criterio de salida.** Al menos 3 de 5 profesionales pagan al terminar el piloto.

---

## F8 · Pase de compra para particulares

**Objetivo.** Abrir la herramienta a particulares en Madrid con pago único.

**Tareas**

- [ ] F8.1 Página de presentación y alta.
- [ ] F8.2 Nivel gratuito: perfil y capacidad de compra.
- [ ] F8.3 Pase de compra con pasarela de pago.
- [ ] F8.4 Derivación a intermediario hipotecario registrado (acuerdo de colaboración).
- [ ] F8.5 Condiciones de uso, política de privacidad y avisos del plan revisados por un abogado.
- [ ] F8.6 Analítica de uso respetuosa con la privacidad.

**Criterio de salida.** Primeros pases vendidos y medición del embudo de registro a pago.

---

## F9 · Medir y decidir

**Objetivo.** Decidir con datos si seguir, ajustar o pivotar.

**Tareas**

- [ ] F9.1 Revisar los criterios: planes que llevan a acción, profesionales que pagan y error de la
      renta estimada.
- [ ] F9.2 Comparar rentas estimadas con las rentas reales conseguidas por los primeros usuarios.
- [ ] F9.3 Decidir siguiente paso: suscripción de propietario, otras ciudades, feeds de agencias o
      NPL y cesiones de remate para profesionales.

**Criterio de salida.** Decisión escrita en un ADR con los datos que la justifican.
