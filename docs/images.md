# Images: upload, storage, and processing

All user uploads go to MinIO (S3-compatible) through django-storages. Processing (resize, crop, WebP encode)
always happens asynchronously in Celery, never in the request. The request returns right away with a
`*processing_status` of `pending`. Clients refetch later to get the processed files.

## Storage

- Backend: `storages.backends.s3boto3.S3Boto3Storage` (`STORAGES["default"]` in `settings.py`).
- One bucket (`MINIO_BUCKET_NAME`). Objects are publicly readable (anonymous `s3:GetObject` only, set by the
  `minio-init` compose service; listing the bucket is *not* allowed). URLs are unsigned (`AWS_QUERYSTRING_AUTH = False`).
- `MINIO_ENDPOINT_URL` is where Django/Celery send S3 API calls (`http://minio:9000` in Docker).
  `MINIO_PUBLIC_URL` (optional) is the browser-reachable host used to build `field.url`.
- `AWS_S3_FILE_OVERWRITE = False`, so a name collision gets a suffix instead of overwriting.
- HEIC/HEIF uploads work because `products/apps.py` registers `pillow_heif` in `ready()`.
- Static files (admin, Swagger) are separate and served by WhiteNoise. They never go to MinIO.

## The three pipelines

| Pipeline | Used by | Output | Task (file) |
|---|---|---|---|
| **Photo + renditions** | product variants, `StoreDiscount.image`, `StoreNews.image` | 3 WebP renditions, aspect ratio kept | `generate_photo_renditions` (`products/tasks.py`) |
| **Category cover** | `StoreCategory.cover` | one 1000×1000 WebP square | `process_category_cover` (`products/tasks.py`) |
| **Buyer avatar** | `Buyer.avatar_photo` | one 500×500 WebP square | `process_buyer_avatar` (`buyers/tasks.py`) |

### 1. Photo + renditions (`StoreProductPhoto` → `StoreProductPhotoRendition`)

Upload paths:

- `POST /api/v1/stores/product-photos/` (multipart, `image`) creates a standalone `StoreProductPhoto`, which is then
  referenced by id from product variants (`variants: [{photos: [id, ...]}]` on product create, or `product-variants`).
- `POST/PATCH /api/v1/stores/news/` and `/api/v1/stores/discounts/` (multipart, `image` file). The serializers call
  `products/photos.py: replace_image()`, which creates a `StoreProductPhoto` behind the scenes and links it through
  the `image` FK. On PATCH: leaving `image` out keeps the current image, `image: null` clears it, and a new file
  creates a *new* photo. In both of the last two cases the **previous photo is deleted**: the row, its renditions,
  and their files in MinIO (`StoreProductPhoto.delete_with_files()`). The exception is a photo that a product
  variant or another news/discount still references (`is_referenced()`), which is kept.
  Deleting the news/discount itself (`DELETE` endpoint) also deletes its photo the same way, via `perform_destroy` →
  `delete_with_image()`, again only if nothing else references the photo.

Flow:

1. The original is saved under key `<photo.uuid>` (no extension). `original_filename` is captured inside
   `product_photo_upload_path`. `processing_status = pending`.
2. `generate_photo_renditions.delay(photo.id)` is called right after the save. It's a plain `.delay()`, not
   `transaction.on_commit`. That's safe today only because requests run in autocommit (no `ATOMIC_REQUESTS`, no
   `atomic` blocks). If that changes, switch to `on_commit` so the worker can't run before the row exists.
3. The worker reads the original and converts the mode (P/CMYK/L → RGB/RGBA) so WebP can encode it. It deletes any
   leftover renditions from an earlier failed attempt, then for each quality:

   | quality | target height |
   |---|---|
   | `large` | 1080 px |
   | `medium` | 720 px |
   | `small` | 320 px |

   It only downscales (an original that is already smaller is copied, never upscaled) and keeps the aspect ratio
   (LANCZOS). Output is WebP at quality 80, stored as `<photo.uuid>_<quality>.webp`.
4. `processing_status = ready`.

Read shape (`StoreProductPhotoSerializer`): `{id, image, original_filename, processing_status, renditions: [{quality, image}, ...]}`.
This shape is nested into product variants, discount `image`, news `image`, and public discount entries on products.
Always prefetch `...renditions` when you serialize photos in a list.

### 2. Category cover (`StoreCategory.cover` → `cover_processed`)

- `StoreCategoryViewSet.perform_create` / `perform_update`: if a `cover` file is sent, it sets
  `cover_processing_status = pending` and queues `process_category_cover`.
- The worker center-crops to 1:1 and resizes to exactly 1000×1000. It **does** upscale small sources so the grid
  stays uniform. The result is saved to `cover_processed` as WebP q80.

### 3. Buyer avatar (`Buyer.avatar_photo` → `avatar_photo_processed`)

- `PATCH /api/v1/customers/me` with `avatar_photo` sets `avatar_processing_status = pending` and queues
  `process_buyer_avatar` (`buyers/views.py`).
- Same center-crop approach as the cover, at 500×500 WebP q80.

## Failure handling (shared by all three)

- Tasks use `bind=True, max_retries=5`, with exponential backoff `min(15 * 2**retries, 300)` s
  (15, 30, 60, 120, 240 s).
- When retries run out, the status becomes `failed` and the exception is re-raised.
- Celery Beat (`birid/celery.py`) runs `sweep_stuck_photo_processing` (photos + category covers) and
  `sweep_stuck_avatar_processing` every 600 s. Each one re-queues rows stuck in `pending` or `failed` with
  `updated_at` older than 15 min. That threshold is longer than the worst-case retry chain (~7.5 min).
  Composite indexes on `(processing_status, updated_at)` keep the sweep cheap.
- Sweep re-queues are capped at `_MAX_SWEEP_RETRIES = 5` per image (in both `products/tasks.py` and
  `buyers/tasks.py`). The count is stored in `processing_retries`, `cover_processing_retries` and
  `avatar_processing_retries`. After 5, the row stays `failed` for good.
  - Uploading a new cover or avatar resets its counter to 0. Product photos are always new rows, so they start at 0.
  - Each re-queue also bumps `updated_at`, so a task that is still waiting in the queue isn't queued a second time.
  - Worst case per image: 1 initial run + 5 sweep runs, each with up to 5 Celery retries.

## Adding images to a new model

- If it needs multiple sizes: add `image = FK(StoreProductPhoto, SET_NULL, null=True)` and reuse the
  News/Discount serializer pattern (`ImageField(write_only=True)`, `_attach_image()`, nested read in
  `to_representation()`, plus a `*ResponseSerializer` for docs). Also prefetch `image__renditions`.
- If it needs one fixed square: copy the cover/avatar pattern (`<field>`, `<field>_processed`,
  `<field>_processing_status`, a task, and an entry in the sweep).
