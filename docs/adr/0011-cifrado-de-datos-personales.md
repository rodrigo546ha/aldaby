# ADR-0011: Cifrado de sobre de los datos personales

**Estado:** Aceptada (D8 del plan de diseño, G4) · **Fecha:** 2026-10-29 · **Decide:** Rodrigo

## Contexto
El perfil del usuario lleva ingresos, deudas, ahorro, base del IRPF y situación familiar. El plan
guarda cifras que se derivan de ellos (cuota máxima, IRPF del alquiler) y el texto que las explica.
La regla 5 de `CLAUDE.md` exige que estén cifrados y que nunca lleguen a los logs ni a los fixtures.
Hoy `user_profiles.data` es un JSONB en claro y `plans.figures` también.

## Decisión
- **Cifrado de sobre.** Cada registro tiene su propia clave de datos (DEK, 32 bytes aleatorios). El
  contenido se cifra con la DEK y la DEK se cifra (envuelve) con una clave maestra (KEK). En la fila
  se guardan el contenido cifrado, la DEK envuelta, el identificador de la KEK y la versión del formato.
- **Algoritmo:** AES-256-GCM (autenticado) para el contenido y para envolver la DEK, con un nonce
  aleatorio de 12 bytes en cada operación. Biblioteca `cryptography` (pyca), la de referencia en Python.
- **Datos asociados (AAD):** tabla, identificador de la fila y organización. Un contenido cifrado no
  se puede mover a otra fila ni a otra organización: al descifrarlo, falla.
- **Claves maestras:** detrás de una interfaz `KeyProvider`.
  - Desarrollo: fichero local fuera del repositorio (`HOUSEFINDER_KEYS_FILE`, por defecto
    `~/.housefinder/master.keys`, permisos 0600), con una o varias claves con identificador; la
    última es la vigente.
  - Producción (F7): AWS KMS con el mismo contrato (el AAD va como contexto de cifrado).
- **Rotación:** se añade una clave nueva; los registros nuevos la usan y `rewrap` cambia solo la DEK
  envuelta de los antiguos, sin volver a cifrar el contenido.
- **Qué se cifra:** el perfil entero (`user_profiles`) y, en `plans`, las entradas, las cifras y el
  texto del agente, en un solo sobre. **En claro** solo lo necesario para filtrar y auditar:
  identificadores, `org_id`, `owner_id`, fechas, versión del motor, huellas de reglas y parámetros y
  `rule_ids`.
- **Redacción:** los modelos de perfil se muestran como `<redactado>` al convertirse en texto, y sus
  errores de validación nunca incluyen los valores recibidos. Un test recorre un flujo completo
  (guardar, leer, rotar, error de validación) con todos los logs en DEBUG y comprueba que no aparecen
  ingresos ni deudas.

## Opciones consideradas
- **pgcrypto en PostgreSQL:** la clave viajaría en cada consulta y podría acabar en los logs del
  servidor. Descartado.
- **Cifrado del disco o del volumen:** necesario en producción, pero no protege de una copia de la
  base, de un volcado ni de un log. Complementario, no suficiente.
- **Una sola clave para todo sin sobre:** rotarla obligaría a volver a cifrar todos los datos.
  Descartado.
- **Fernet (también de `cryptography`):** más sencillo, pero sin datos asociados para atar el
  contenido a su fila. Descartado.

## Consecuencias
- No se puede buscar ni filtrar por campos del perfil en SQL: solo por los metadatos en claro.
- Sin la clave maestra los datos no se pueden leer. Perder el fichero de claves en desarrollo
  significa perder los perfiles de desarrollo; en producción, KMS guarda la clave.
- **Supresión (RGPD):** borrar la fila borra el dato. Las copias de seguridad lo conservan hasta su
  caducidad, porque la DEK va en la misma fila; borrado criptográfico inmediato exigiría una KEK por
  usuario. Revisar en F7.
- `cryptography` pasa a ser dependencia de la API.
