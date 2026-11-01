# ADR-0028: Despliegue y acceso de la beta

- **Estado:** aceptada (decisiones de Rodrigo, 2026-11-01)
- **Fecha:** 2026-11-01
- **Tarea:** F7.1 y F7.5

## Contexto
PLAN_DE_DESARROLLO (sección 3.3) deja pendiente dónde se despliega la beta; ADR-0011 y PLAN_DISENO
decían AWS, y el plan proponía Vercel, Supabase y un servidor GPU. Rodrigo pide **lo más barato**,
con el modelo en un servidor con GPU. También hay que decidir cómo entran los profesionales y cómo
se separan los datos de cada uno (D10).

## Decisión

### Un solo servidor con GPU en la UE
- **Hetzner GEX45:** 14 núcleos, 64 GB de memoria y una RTX PRO 4000 Blackwell de 24 GB.
  - **Precio** (página oficial, 2026-11-01): 214 € al mes o 0,3429 € la hora, más 209 € de alta,
    sin IVA.
  - **Ubicación:** Falkenstein o Helsinki.
  - **Lo que cabe:** el GEX44 que citaba el plan ya no se ofrece, y este es el servidor con GPU
    más barato de Hetzner. Con esa memoria caben también la web, la API, el worker y la base, así
    que no hace falta un segundo servidor.
- **Docker Compose** con:
  - Caddy (HTTPS con Let's Encrypt);
  - la web (Next.js);
  - la API (FastAPI, con pango para WeasyPrint y Tesseract);
  - el worker;
  - PostgreSQL con PostGIS;
  - el servidor del modelo (Ollama, como en desarrollo).
  Los 24 GB permiten probar modelos mayores que el de desarrollo (F6.0).
- **Se contrata al montar F7.5**, poco antes del piloto: no antes. Hasta entonces todo sigue en el
  Mac.
- **Alternativas más baratas, a comprobar cuando se contrate:**
  - la subasta de servidores de Hetzner, si aparece uno con GPU de al menos 16 GB (qwen3:14b
    ocupa unos 10 GB);
  - otros proveedores europeos de GPU de 16 GB.
  Ninguna está verificada.

### Claves y copias
- **Clave maestra (ADR-0011) en un fichero del servidor,** con permisos 0600 y fuera de la imagen y
  de las copias. Sin KMS en la beta: quien tenga acceso de administrador al servidor tiene la
  clave. Mitigación: SSH solo con clave y sin contraseña. Revisar al pasar de la beta.
- **Copia diaria de la base** con `pg_dump`, cifrada antes de salir del servidor, a almacenamiento
  externo (Storage Box de Hetzner u otro). La clave maestra se guarda aparte. Detalle en F7.5.

### Acceso con correo y contraseña
- **Contraseñas con argon2id** (`argon2-cffi`, licencia MIT). Mínimo de doce caracteres y sin más
  reglas de composición. Comparación en tiempo constante.
- **Sesiones en la base:** un token aleatorio de 32 bytes en una cookie `HttpOnly`, `Secure` y
  `SameSite=Lax`. Se guarda solo su hash SHA-256. Caduca a los catorce días sin uso y se cierra
  al salir. La web llama a la API por el mismo origen (`/api`), así que la cookie no sale del
  dominio.
- **Altas por el administrador** (beta privada, sin registro abierto).
  `python -m housefinder.accounts alta …` crea la cuenta en su organización y devuelve un enlace
  de un solo uso, válido siete días, para que el profesional elija su contraseña. Rodrigo lo
  envía. El mismo mecanismo sirve para restablecer una contraseña. No hace falta un servicio de
  correo en la beta.
- **Freno a los intentos:** cinco fallos seguidos de una cuenta la bloquean quince minutos. El
  mensaje de error es el mismo exista o no la cuenta.
- **Roles:** `admin` (Rodrigo) y `profesional`. Los clientes de un profesional (F7.2) no tienen
  cuenta: son perfiles de su organización.

### Separación de datos por organización
- **La organización sale de la sesión,** nunca del cliente. `get_org` deja de usar la
  organización local de desarrollo, salvo con `HOUSEFINDER_DEV_ORG=1`, que solo se pone en el Mac.
- **Row-Level Security de PostgreSQL** en las tablas con `org_id`:
  - perfiles, entrevistas, planes y rentas esperadas: solo las filas de su organización;
  - ofertas: las suyas y las públicas (`org_id IS NULL`, lotes del BOE).
  La API trabaja con un rol sin privilegios de propietario (`housefinder_api`, con `SET ROLE` al
  abrir la conexión) y fija `app.org_id` en cada petición. El propietario, con el que van las
  migraciones y el worker, no está sujeto a las políticas: necesita ver todo. Es una segunda
  barrera: el código ya filtra por `org_id`.

## Opciones consideradas
- **Servidor pequeño sin GPU y el modelo en el Mac por un túnel:** lo más barato, pero sin modelo
  cuando el Mac está apagado. Rodrigo prefiere GPU.
- **Vercel, Supabase y servidor GPU:** tres proveedores y la API partida por el límite de duración
  de las funciones.
- **AWS:** más piezas y más caro para una persona a tiempo parcial.
- **Enlace mágico por correo:** sin contraseñas, pero necesita un servicio de envío desde el primer
  día.

## Consecuencias
- Una dependencia nueva (`argon2-cffi`) y dos tablas (cuentas y sesiones), con su migración.
- Las copias, las actualizaciones y la vigilancia del servidor son nuestras (F7.5).
- La clave maestra en fichero es aceptable para una beta cerrada; no para un lanzamiento abierto.
