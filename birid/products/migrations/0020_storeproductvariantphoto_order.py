# Turns the auto-created StoreProductVariant.photos join table into an explicit through model with an `order` column.
# Django can't ALTER an M2M into a through model, so the existing table is renamed in place (rows and ids kept)
# and the state is updated separately (SeparateDatabaseAndState: state and SQL differ on purpose).

import django.db.models.deletion
from django.db import migrations, models


FORWARD_SQL = """
ALTER TABLE products_storeproductvariant_photos RENAME TO products_storeproductvariantphoto;
ALTER TABLE products_storeproductvariantphoto RENAME COLUMN storeproductvariant_id TO variant_id;
ALTER TABLE products_storeproductvariantphoto RENAME COLUMN storeproductphoto_id TO photo_id;
ALTER TABLE products_storeproductvariantphoto ADD COLUMN "order" integer NOT NULL DEFAULT 0;
ALTER TABLE products_storeproductvariantphoto ALTER COLUMN "order" DROP DEFAULT;
-- Existing links had no position; number them in insertion order so the current gallery order is kept.
UPDATE products_storeproductvariantphoto AS t
SET "order" = s.rn
FROM (
    SELECT id, row_number() OVER (PARTITION BY variant_id ORDER BY id) - 1 AS rn
    FROM products_storeproductvariantphoto
) AS s
WHERE t.id = s.id;
-- Replace the auto-generated unique(variant, photo) with the named one from Meta.constraints.
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT conname FROM pg_constraint
             WHERE conrelid = 'products_storeproductvariantphoto'::regclass AND contype = 'u'
    LOOP
        EXECUTE format('ALTER TABLE products_storeproductvariantphoto DROP CONSTRAINT %I', r.conname);
    END LOOP;
END $$;
ALTER TABLE products_storeproductvariantphoto
    ADD CONSTRAINT uniq_photo_per_variant UNIQUE (variant_id, photo_id);
"""

REVERSE_SQL = """
ALTER TABLE products_storeproductvariantphoto DROP CONSTRAINT uniq_photo_per_variant;
ALTER TABLE products_storeproductvariantphoto DROP COLUMN "order";
ALTER TABLE products_storeproductvariantphoto RENAME COLUMN variant_id TO storeproductvariant_id;
ALTER TABLE products_storeproductvariantphoto RENAME COLUMN photo_id TO storeproductphoto_id;
ALTER TABLE products_storeproductvariantphoto RENAME TO products_storeproductvariant_photos;
ALTER TABLE products_storeproductvariant_photos
    ADD CONSTRAINT products_storeproductvariant_photos_unique UNIQUE (storeproductvariant_id, storeproductphoto_id);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0019_storeproduct_slug_global_unique'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='StoreProductVariantPhoto',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('order', models.PositiveIntegerField(default=0)),
                        ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variant_links', to='products.storeproductphoto')),
                        ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photo_links', to='products.storeproductvariant')),
                    ],
                    options={
                        'ordering': ['order', 'id'],
                        'constraints': [models.UniqueConstraint(fields=('variant', 'photo'), name='uniq_photo_per_variant')],
                    },
                ),
                migrations.AlterField(
                    model_name='storeproductvariant',
                    name='photos',
                    field=models.ManyToManyField(blank=True, related_name='variants', through='products.StoreProductVariantPhoto', to='products.storeproductphoto'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
            ],
        ),
    ]
