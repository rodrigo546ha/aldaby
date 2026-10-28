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
- [ ] F1.10 Endpoint `POST /simulate/investment` y página web del simulador de capacidad.

**Criterio de salida.** Todos los cálculos con test de valor conocido, cifras como `Figure`, y un
plan manual de F0 reproducido por el motor con diferencias menores de 1 €.

---

## F2 · Normativa y fiscalidad

**Objetivo.** Que cada regla legal que afecta a la rentabilidad esté en datos, verificada y con fecha.

**Tareas**

- [x] F2.1 Motor `RuleBook`: territorio jerárquico, vigencia, estado y verificación.
- [x] F2.1a Catálogo de tipos de regla con esquema de parámetros y validador de reglas
      (`make rules-check`, también en CI): territorios, vigencias solapadas y revisor obligatorio.
- [ ] F2.2 Inventario de reglas necesarias para Madrid: impuesto de compra (segunda mano y obra
      nueva), gastos de notaría y registro, IBI orientativo, reducción del rendimiento del alquiler,
      amortización fiscal, mínimos de IRPF relevantes.
- [ ] F2.3 Cargar cada regla desde la fuente oficial con `verified: true` tras revisión.
- [ ] F2.4 Normativa de alquiler: zonas tensionadas (lista oficial), alquiler de temporada, por
      habitaciones y turístico (mayoría de 3/5 de la comunidad, registro autonómico).
- [ ] F2.5 Escenarios: reglas `pendiente_convalidacion` y comparación «con / sin» en el plan.
- [ ] F2.6 Monitor del BOE y del BOCM: detectar disposiciones nuevas sobre vivienda y abrir una
      tarea de revisión (la IA resume, una persona decide).
- [ ] F2.7 Conectar `TaxParams` del motor de cash flow con `RuleBook`, citando `rule_ids`.

**Criterio de salida.** Un plan de Madrid sale con todas sus reglas citadas y verificadas, y cambiar
una ley solo requiere añadir una regla en YAML.

---

## F3 · Datos territoriales

**Objetivo.** Conocer cada zona por sección censal: quién vive, cuánto gana, cómo evoluciona.

**Tareas**

- [ ] F3.1 Base de datos local con `make db` y migración `0001_init.sql`.
- [ ] F3.2 Cargar la cartografía de secciones censales del INE para la Comunidad de Madrid.
- [ ] F3.3 Cargar el Atlas de Distribución de Renta de los Hogares (INE) por sección.
- [ ] F3.4 Cargar el padrón (población, edad, nacionalidad) y su evolución.
- [ ] F3.5 Indicadores de demanda: universidades y matrícula, hospitales y grandes empleadores,
      afiliación a la Seguridad Social por municipio.
- [ ] F3.6 Geocodificación con CartoCiudad y asignación de sección censal a una dirección.
- [ ] F3.7 Registro de cada carga en `sources` (url, licencia, fecha).

**Criterio de salida.** Dada una dirección de Madrid, la API devuelve su sección censal con renta,
población y tendencias, cada valor con su fuente.

---

## F4 · Ingesta de oferta

**Objetivo.** Tener oferta real que analizar por tres canales legales.

**Tareas**

- [ ] F4.1 Enlace pegado por el usuario: descargar la página que el usuario aporta, extraer los datos
      con el agente (precio, superficie, planta, estado, fotos) y pedir confirmación al usuario.
- [ ] F4.2 Verificar la API de datos abiertos del BOE con un sumario real y guardarlo como fixture;
      ajustar `ingestion/boe.py` a su esquema.
- [ ] F4.3 Subastas del Portal de Subastas del BOE para la provincia de Madrid (revisar condiciones
      de uso; si no hay vía de datos abiertos, ADR antes de implementar).
- [ ] F4.4 Anuncios de la sección V del BOE: Seguridad Social, INVIED, Patrimonio del Estado.
- [ ] F4.5 Servicers (Solvia, Servihabitat, Aliseda, Altamira, Hipoges): revisar términos de uso de
      cada web, ADR por servicer y contacto comercial para acuerdo.
- [ ] F4.6 Normalización y deduplicación por referencia catastral y geolocalización.
- [ ] F4.7 Trabajos programados con reintentos y alertas de fallo.

**Criterio de salida.** Cada día entran ofertas nuevas de al menos dos canales, sin duplicados, con
sección censal asignada.

---

## F5 · Valoración

**Objetivo.** Estimar renta y precio de cada inmueble con un rango honesto.

**Tareas**

- [ ] F5.1 Recopilar referencias de precio: Portal Estadístico del Notariado, valor tasado del
      Ministerio, IPV del INE (revisar términos de reutilización).
- [ ] F5.2 Referencias de alquiler: Sistema Estatal de Referencia del Precio del Alquiler e IPVA.
- [ ] F5.3 Modelo base de renta por sección, superficie y características, con intervalo P25–P75.
- [ ] F5.4 Modelo base de precio y margen de negociación respecto al precio pedido.
- [ ] F5.5 Escenarios de revalorización (conservador, base, optimista) a partir de factores
      explicables: población, empleo, renta, oferta nueva.
- [ ] F5.6 Backtesting: qué habría estimado el modelo con datos de años anteriores.

**Criterio de salida.** Error medio de la renta estimada frente a referencias reales por debajo del
umbral fijado en F0, y cada estimación con su rango.

---

## F6 · Agente y plan de inversión

**Objetivo.** Del perfil al plan completo, explicado y exportable.

**Tareas**

- [ ] F6.1 Interfaz propia para el LLM (Claude en AWS Bedrock), intercambiable por configuración.
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
