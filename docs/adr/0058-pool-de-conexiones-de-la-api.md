# ADR-0058: Pool de conexiones de la API

- **Estado:** aceptada
- **Fecha:** 2026-11-05

## Contexto

La API abría una conexión nueva a PostgreSQL en cada petición (`get_db`) y la cerraba al acabar.

Medido en este Mac, contra la base de Docker, 15 veces cada caso:

| Caso | Mediana | Máximo |
|---|---|---|
| Abrir la conexión, `SET ROLE` y una consulta | 282 ms | 436 ms |
| Lo mismo con una conexión ya abierta | 7 ms | — |

Cada pantalla hace varias llamadas (`/auth/me`, `/clients`, el catálogo, la búsqueda…), y cada una
pagaba esos 280 ms antes de empezar a trabajar.

Cada petición deja estado en su sesión de PostgreSQL:
- el rol `housefinder_api`, para que le apliquen las políticas de Row-Level Security (ADR-0028);
- `app.org_id`, la organización con la que filtran esas políticas, con `set_config(..., false)`.

Con conexiones reutilizadas, ese estado pasaría a la petición siguiente: una petición sin
organización podría ver los datos de la organización anterior.

## Decisión

1. **Dependencia nueva:** `psycopg-pool`, el pool oficial del proyecto psycopg. Es la misma familia
   que el conector que ya usamos (`psycopg`) y no trae más dependencias. Solo la importa `db/`, como
   `psycopg` (la regla de arquitectura ya lo contemplaba).
2. **Un pool por URL de base**, abierto la primera vez que se usa (`db.connection.pooled`):
   - `get_db` toma una conexión del pool en vez de abrir una;
   - los trabajos, las órdenes de terminal y las ingestas siguen con `connect()`, una conexión
     propia.
3. **Limpieza al devolver cada conexión** (`reset`):
   - se ejecutan `RESET ROLE` y `RESET ALL`, y se confirma;
   - si la limpieza falla, el pool descarta esa conexión;
   - toda conexión vuelve al pool sin rol y sin organización, sea cual sea el resultado de la
     petición: bien, con error o con excepción.
4. **Comprobación al prestarla** (`check`): se descarta una conexión que la base haya cerrado
   (reinicio de Docker, base de tests borrada) en vez de dársela a una petición.
5. **Tamaño:**
   - de 1 a 10 conexiones, configurable con `DB_POOL_MAX`;
   - si todas están ocupadas más de 10 s, la petición recibe 503, como cuando la base no responde;
   - los pools se cierran al parar la API.

## Consecuencias

- Cada llamada a la API se ahorra unos 280 ms en este Mac. En el servidor de la beta la base va en
  la misma máquina (ADR-0040), así que la mejora será menor, pero sigue sin hacer falta abrir
  conexiones.
- Medido después, mediana de cinco llamadas:

  | Llamada | Antes | Ahora |
  |---|---|---|
  | `/auth/me` | 185 ms | 2 ms |
  | `/clients` | 330–440 ms | 7 ms |
  | `/profile/current` | 520–580 ms | 9 ms |
  | `/offers/catalog/{id}` | 420–500 ms | 10 ms |

  Navegando, la ficha desde el mapa pasa a 41 ms, el plan completo a 172 ms y la vuelta al mapa a
  26 ms.
- Un test comprueba que una conexión devuelta al pool no conserva ni el rol ni `app.org_id`.
- Hay que añadir `psycopg-pool` a la imagen de la API (`infra/produccion/requisitos-api.txt`, que
  `make requisitos-api` genera desde el entorno probado).
