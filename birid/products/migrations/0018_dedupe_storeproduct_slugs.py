from django.db import migrations

_SLUG_MAX_LENGTH = 255


def dedupe_slugs(apps, schema_editor):
    """
    Slugs used to be unique per store only - before making them globally
    unique (next migration), suffix every repeat after the oldest one:
    `plate`, `plate` -> `plate`, `plate-2`. Candidates are checked against
    every existing slug so a rename can't collide with another product's.
    """
    StoreProduct = apps.get_model("products", "StoreProduct")
    taken = set(StoreProduct.objects.values_list("slug", flat=True))
    seen = set()
    for product_id, slug in StoreProduct.objects.order_by("id").values_list("id", "slug"):
        if slug not in seen:
            seen.add(slug)
            continue
        n = 2
        while True:
            suffix = f"-{n}"
            candidate = slug[:_SLUG_MAX_LENGTH - len(suffix)] + suffix
            if candidate not in taken:
                break
            n += 1
        taken.add(candidate)
        seen.add(candidate)
        StoreProduct.objects.filter(id=product_id).update(slug=candidate)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0017_storecategory_cover_processing_retries_and_more'),
    ]

    operations = [
        migrations.RunPython(dedupe_slugs, migrations.RunPython.noop),
    ]
