# Imagen de las copias (ADR-0040): pg_dump y pg_restore de PostgreSQL 16 junto a restic, para que
# `restic backup --stdin-from-command -- pg_dump …` no guarde una copia a medias si pg_dump falla.
FROM restic/restic:0.19.1 AS restic

FROM postgres:16-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=restic /usr/bin/restic /usr/bin/restic
ENTRYPOINT []
CMD ["restic", "version"]
