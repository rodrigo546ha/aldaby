# HouseFinder

Planes de inversión inmobiliaria personales: encuentra el inmueble que encaja con tu situación
financiera y calcula lo que te rinde a ti, con tu hipoteca, tus impuestos y tu tiempo.

## Empezar en 5 minutos

```bash
cp .env.example .env
make setup      # Python y dependencias web
make test       # los motores deben salir en verde
make api        # http://localhost:8000/docs
```

Prueba el simulador de capacidad de compra:

```bash
curl -X POST localhost:8000/simulate/affordability -H 'Content-Type: application/json' \
  -d '{"net_monthly_income":4000,"available_savings":60000,"age":30,"annual_rate":0.03,"purchase_cost_rate":0.10}'
```

## Documentación

- [CLAUDE.md](CLAUDE.md): reglas del proyecto e instrucciones para Claude Code.
- [docs/ROADMAP.md](docs/ROADMAP.md): planning por fases y fase activa.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): arquitectura y flujo de datos.
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md): fuentes de datos y su estado.
- [docs/adr/](docs/adr/): decisiones de arquitectura.
