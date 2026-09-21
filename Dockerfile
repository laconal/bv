FROM python:3.14-slim

WORKDIR /app

# slim (glibc), not alpine - psycopg[binary]/argon2-cffi/pillow all publish
# manylinux wheels but not reliably musllinux ones; building from source on
# alpine would need a much heavier toolchain for no real benefit here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY birid ./birid
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

WORKDIR /app/birid
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "birid.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
