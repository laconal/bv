# Birid — clothing marketplace backend

API-only Django backend (no frontend in this repo) for a multi-store clothing marketplace.
Two kinds of users: **store admins** (manage one store's catalog, news, discounts, orders) and
**buyers** (browse, favorite, place orders). Anonymous visitors can browse the public endpoints.

Stack: Python 3.14, Django 6 + Django REST Framework + drf-spectacular, PostgreSQL (via PgBouncer),
MinIO (S3) for media via django-storages, Celery + Redis for image processing, gunicorn + WhiteNoise.
Dependencies are managed with `uv` (`pyproject.toml`, `uv.lock`).

## Deeper docs (read on demand, not every time)

- [docs/models.md](docs/models.md) — every model, its key fields, and how they relate (ER diagram).
- [docs/images.md](docs/images.md) — how images are uploaded, stored, and converted to lower-quality WebP renditions.
- [docs/api-conventions.md](docs/api-conventions.md) — URLs, auth, tenancy, `get-all` filtering/pagination, schema-doc patterns, checklist for adding a resource.

## Layout

```
/                      repo root: pyproject.toml, docker-compose.yaml, Dockerfile, entrypoint.sh, .env(.example)
birid/                 Django project root (manage.py lives here — run all manage.py commands from here)
  birid/               settings.py, urls.py, celery.py (beat schedule)
  core/                shared infra: abstract auth model, JWT, filtering, pagination, exception handler, viewset bases
  stores/              Store, StoreAdmin (+ auth), store profile config (addresses, contacts, socials, services, colors, icons)
  buyers/              Buyer (+ auth), favorites, avatar processing task
  products/            catalog: categories, tags, materials, products, photos + renditions, variants, discounts, reports
  news/                StoreNews
  orders/              StoreOrder / StoreOrderItem, checkout, status state machine
```

Per-app file convention: `viewsets.py` + `urls.py` = store-admin side; `public_viewsets.py` + `public_urls.py`
= anonymous side; `customer_*.py` = buyer side (orders); `tasks.py` = Celery; `serializers.py`, `models.py`.

## Commands

All from `birid/`. Settings require env vars; without a real `.env`, source the example
(enough for `check`/`makemigrations`/schema — JWT key files are read lazily, DB isn't needed):

```bash
cd birid && set -a && source ../.env.example && set +a
python manage.py check
python manage.py makemigrations <app>          # warns about DB connection when no DB is running — harmless
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file /tmp/schema.yaml   # validates OpenAPI generation
```

Full stack: `docker compose up -d --build` from repo root (postgres, pgbouncer, redis, minio, minio-init,
django, celery-worker, celery-beat). Migrations + collectstatic run automatically in the `django` container only
(`entrypoint.sh`). Swagger UI: `http://localhost:8000/api/v1/docs/`.

There are **no real tests** yet (every `tests.py` is a stub; `pytest-django` is not installed).
`README.md` is outdated (mentions `src/core/secrets`, `salonBackend`) — trust this file and `entrypoint.sh` over it.
Root `test.py` and `celerybeat-schedule` are scratch/artifacts, not part of the app.

## Conventions that matter

- **Tenancy**: store-admin viewsets subclass `stores.viewsets.StoreScopedModelViewSet` — queryset is filtered to
  `request.user.store` and `store` is injected on create. Never accept `store` from the request body.
  Serializers validate that referenced objects (category, tags, color, photos…) belong to `request.user.store`.
- **Auth is custom JWT, not Django sessions/SimpleJWT**. Each view sets `authentication_classes` explicitly
  (`StoreAdminJWTAuthentication` or `BuyerJWTAuthentication`); global default is none + `IsAuthenticated`.
  Public views use `AllowAny`.
- **Lists are `POST .../get-all`** with `{filters, page, pageSize}` — `GET` list is disabled. Filterable fields are
  each model's `ALLOWED_FILTERS` set (see `core/filtering.py`). Adding a filterable field = add it to `ALLOWED_FILTERS`
  and to the `filters_example` in the viewset's `@tagged(...)` decorator.
- **No PUT** — only PATCH (`NoPutModelViewSet`).
- **N+1 discipline**: list querysets prefetch everything the serializer touches (`PRODUCT_PREFETCH`,
  `prefetch_active_discounts()`, `image__renditions`, …). Keep this when adding nested fields.
- **Write-id / read-nested fields**: when a serializer accepts a plain value but returns a nested object via
  `to_representation()`, add a doc-only `*ResponseSerializer` subclass and `@extend_schema_view(...)` so Swagger is
  right (see `StoreProductResponseSerializer`, `StoreDiscountResponseSerializer`, `StoreNewsResponseSerializer`).
- **Postgres-only features are fine** (`ArrayField`, `__overlap`, `django.contrib.postgres` is installed).
  Server-side cursors are disabled because of PgBouncer transaction pooling.
- **Migrations that change a column type** (e.g. scalar → array) need a hand-written `RunSQL ... USING` inside
  `SeparateDatabaseAndState` — see `products/migrations/0015_alter_storeproduct_size.py`.
- Comments in this codebase explain *why* (constraints, invariants), not *what*. Keep that style; Russian is used in
  `filters_example` sample values (the UI language), English everywhere else.

## Gotchas

- `.env` lives at the repo root, but JWT key paths in it resolve relative to `birid/` (`BASE_DIR`).
- `CORS_ALLOW_ALL_ORIGINS = True` — intentionally open for now; `CSRF_TRUSTED_ORIGINS` still comes from env.
- Product `slug` is unique across **all** stores (not per store) — public lookup: `GET /public/products/by-slug/<slug>/`.
  It's optional on input: generated from the name when missing, auto-suffixed (`-2`, `-3`) on conflict — see docs/models.md.
- Product `size` is a list of ints (`ArrayField`); an order item's `size` is a single int validated against it.
- Public product listing hides products whose `category` or `subcategory` has `visible=False`.
- Orders keep an immutable `product_snapshot` JSON — never read live product data to describe a past order.
