# API conventions

## URL map (`birid/birid/urls.py`)

| Prefix | Who | Auth class | Contents |
|---|---|---|---|
| `/api/v1/stores/` | store admin | `StoreAdminJWTAuthentication` | `login`, `refresh`, `me`, `store` (own profile), `social-links`, `addresses`, `contacts`, `services`, `colors`, `icons`, `categories`, `tags`, `product-material-categories`, `product-materials`, `products`, `product-variants`, `product-photos` (+ `{id}/download`), `discounts`, `news`, `orders` |
| `/api/v1/stores/reports/` | store admin | same | `summary`, `most-viewed-products`, `most-favorited-products`, `most-popular-categories` (POST, `from_date`/`to_date`, default last 30 days) |
| `/api/v1/customers/` | buyer | `BuyerJWTAuthentication` | `login`, `refresh`, `me` (GET/PATCH, avatar), `favorites/products/<id>`, `favorites/stores/<id>` (POST add / DELETE remove), `favorites/*/get-all`, `orders` (checkout, list, retrieve, cancel) |
| `/api/v1/public/` | anyone | none, or buyer token optional on products | `stores`, `stores/<store_pk>/categories` (visible categories of one store), `products` (+ `products/by-slug/<slug>/`), `news` (read-only) |
| `/api/v1/schema/`, `/api/v1/docs/` | — | — | OpenAPI + Swagger UI |
| `/admin/` | Django staff | session | Django admin (uses Django's built-in `User`, unrelated to API users) |

URL paths for the custom `APIView`s have **no trailing slash** (`login`, `me`, `store`). Router-based viewsets use
the DRF default **with** a trailing slash (`products/`, `products/{id}/`, `products/get-all/`).

## Authentication

- RS256 JWT, built in-house: `core/jwt.py` (`JWTIssuer`) and `core/authentication.py` (`BaseJWTAuthentication`).
- Store admins and buyers each have their **own keypair** (`stores/security.py`, `buyers/security.py`), so a token
  for one kind of user is rejected on the other's endpoints.
- `POST login {login, password}` returns `{access, refresh}`. `POST refresh {refresh}` returns a new pair.
  Send the token as `Authorization: Bearer <access>`.
- TTLs come from env: admin access 1 d / refresh 7 d, buyer access 30 min / refresh 30 d (defaults in `.env.example`).
- Passwords use argon2 (`AbstractAuthAccount.check_password`). There's no sign-up endpoint yet, so accounts are
  created in the admin or the shell.
- Bad credentials raise `core.exceptions.InvalidCredentials` (401). It doesn't use DRF's `AuthenticationFailed`
  because DRF turns that into a 403 on views with no `authentication_classes`, which includes the login views.

## Tenancy

`stores.viewsets.StoreScopedModelViewSet` (base class for every store-admin CRUD viewset):

- `get_queryset()` filters by `store=request.user.store`, so another store's ids return 404.
- `perform_create()` calls `serializer.save(store=request.user.store)`. The serializer sees `store` inside
  `validated_data` in `create()`.
- Serializers also check that every referenced object (category, subcategory, tags, materials, color, photos,
  products, …) has `store_id == request.user.store_id`.

## Listing: `POST .../get-all`

`GET` on a list endpoint returns 405. Lists are requested like this:

```json
POST /api/v1/public/products/get-all/
{
  "filters": {
    "category": 1,
    "name": "Платье",
    "tags": [1, 2],
    "size": [40, 42],
    "price_sale": {"gte": "1000.00", "lte": "20000.00"},
    "created_at": {"gte": "2026-01-01"}
  },
  "page": 1,
  "pageSize": 20
}
```

The response is `{items, page, totalPages, total}` (the same envelope `paginate_body` uses everywhere).

Filter rules (`core/filtering.py: apply_filters`). Only fields listed in the model's `ALLOWED_FILTERS` are used;
unknown keys are silently ignored.

| Value shape | Lookup |
|---|---|
| string on a Char/Text field without choices | `icontains` |
| any other scalar | exact |
| list | `__in` |
| `{"eq"/"gt"/"gte"/"lt"/"lte": v}` | comparison; an unknown operator returns 400 |
| any value on an `ArrayField` (e.g. `size`) | `__overlap` (matches if any value is present); comparison dicts return 400 |
| `created_at` / `updated_at` | compared by **date only** (`__date`) |

Filtering through an M2M field adds `.distinct()`.

## Viewset building blocks (`core/viewsets.py`)

- `NoPutModelViewSet`: full CRUD with PATCH only (no PUT), plus `get-all`.
- `PublicReadOnlyViewSet`: retrieve plus `get-all`.
- `@tagged(tag, ResponseSerializer, filters_example={...})` / `@public_tagged(...)` set the drf-spectacular tags,
  summaries, the paginated response schema and the `get-all` request example. **Keep `filters_example` in sync with
  `ALLOWED_FILTERS`**, because it is the only filter documentation the frontend sees.
- `COMPONENT_SPLIT_REQUEST = True` gives separate `XRequest`/`X` schemas, so file fields show up as binary uploads.
- `ENUM_NAME_OVERRIDES` in settings removes duplicate identical choice sets. If you add a new choice set that matches
  an existing one, add an override, otherwise `spectacular` will warn.

## Write-shape ≠ read-shape pattern

Examples: `StoreProductSerializer.variants`, plus `image` on `StoreDiscountSerializer` and `StoreNewsSerializer`.

1. The field is write-only on input (ids, or a file).
2. `to_representation()` swaps in the nested read shape.
3. A doc-only subclass `XResponseSerializer` redeclares the field with its read shape.
4. The viewset gets `@extend_schema_view(retrieve=..., create=..., update=..., partial_update=...)` pointing at it,
   and `@tagged(...)` gets the response serializer.

## Errors

`core/exceptions.py: custom_exception_handler` turns Postgres `IntegrityError` SQLSTATEs into JSON responses:

| SQLSTATE | Meaning | HTTP |
|---|---|---|
| 23505 | unique violation | 409 |
| 23503 | foreign key violation | 404 |
| 23502 | not null violation | 409 |
| 23514 | check violation | 409 |
| other | — | 409 `integrity_error` |

DRF validation errors keep the normal `{field: [messages]}` shape.

## Checklist: adding a new store-scoped resource

1. Model: add a `store` FK, `TimestampedModel`, `ALLOWED_FILTERS`, and per-store unique constraints if needed.
2. Run `makemigrations <app>`. Check the generated file (column type changes need `RunSQL ... USING`).
3. Serializer: add tenancy `validate_<fk>` checks for every FK/M2M the client can set.
4. Viewset: subclass `StoreScopedModelViewSet`, prefetch whatever the serializer reads, and decorate with
   `@tagged(..., filters_example=...)`.
5. Register it on the app's router (`urls.py`). If it's public, also add a `PublicReadOnlyViewSet` that filters
   `store__active=True` plus any visibility/status rules.
6. Verify: `manage.py check`, `makemigrations --check --dry-run`, `manage.py spectacular --file /tmp/s.yaml`
   (it should print no warnings).
