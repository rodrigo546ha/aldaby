# ADR-0060: La renta crece en la TIR con el IPC de alquiler de la comunidad

- **Estado:** aceptada
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («Sí, sigue», sobre hacer crecer la renta en la TIR)

## Contexto

La TIR (`engines/irr.py`) supone la renta constante durante todo el horizonte: el cash flow del
año 10 es el del año 1. A diez años, eso infravalora la TIR de cualquier inversión en alquiler.

El componente de alquiler del IPC del INE por comunidad (`ine-ipc-alquiler`, ADR-0018) está cargado
de 2002 a 2026 para las diecinueve comunidades y ciudades autónomas. Mide los alquileres en vigor,
no los nuevos contratos. Eso es lo que interesa aquí: es la renta que paga un inquilino a lo largo
del tiempo, con sus actualizaciones, los topes legales de cada época y las renovaciones.

## Decisión

1. **Subida anual de la renta** = la mediana del crecimiento anual compuesto de todas las ventanas
   históricas del IPC de alquiler de la comunidad de la duración del horizonte. Las ventanas son
   de mes a mes: con 24 años de serie y un horizonte de 10, hay unas 170. Es el mismo método que el
   ciclo del IPV en la revalorización (F5.5). Si no hay al menos ocho ventanas, se acorta la
   ventana; si ni con ventanas de un año hay ocho, la renta queda constante y el plan lo dice.
2. **Cifra propia, `assumption.rent_growth`,** con la fórmula (ventanas, periodo y percentil) y la
   fuente con su último mes. Va en el bloque de venta y rentabilidad, junto a la revalorización.
3. **Cómo se aplica:** el año 1 no cambia. Desde el año 2, la renta es la del año 1 ×
   (1 + subida)^(año − 1). La gestión, el mantenimiento y el vacío son porcentajes de la renta, así
   que suben con ella. El IRPF de cada año se calcula con la renta de ese año.
4. **Dónde:** la TIR de cada escenario de revalorización y la serie del cash flow año a año
   (ADR-0050). La prueba de estrés, el plazo recomendado y el cash flow del primer año no cambian:
   miran el primer año.
5. **Una sola subida para los tres escenarios de revalorización.** Cruzarlas multiplicaría los
   escenarios sin una fuente que diga cómo se mueven juntas.

## Consecuencias

- La TIR sube en las comunidades donde el alquiler ha crecido. La búsqueda inversa ordena por TIR
  en los objetivos «revalorización» y «mixto», así que el orden puede cambiar.
- **Los gastos fijos siguen constantes:** comunidad, IBI y seguro. Con la renta creciendo, la TIR
  queda algo optimista. Hacerlos crecer con el IPC general pide cargar esa serie, que hoy no está:
  es una fuente nueva y se decide aparte.
- **Topes futuros:** la serie histórica ya recoge los topes de actualización de cada época, pero no
  sabe de los que vengan. Un tope legal nuevo a la actualización de la renta (por ejemplo, ligado a
  un índice de referencia) iría como regla en `data/rules`, no en el código, y no está cargado.
- **Zona tensionada:** el IPC es de toda la comunidad. En una zona tensionada la renta de los
  contratos nuevos está limitada y puede crecer menos que la media. El plan ya avisa de la zona;
  la subida no se ajusta por ella.
