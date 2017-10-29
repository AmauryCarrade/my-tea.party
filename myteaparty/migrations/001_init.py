"""Peewee migrations -- 001_init.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

import datetime as dt
import peewee as pw

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    tables = database.get_tables()

    if 'tea_vendors' not in tables:
        @migrator.create_model
        class TeaVendor(pw.Model):
            description = pw.CharField(max_length=255)
            link = pw.CharField(max_length=255)
            logo = pw.CharField(max_length=255, null=True)
            name = pw.CharField(max_length=255)
            twitter = pw.CharField(max_length=255, null=True)
            slug = pw.CharField(max_length=255, unique=True)
            order = pw.IntegerField(default=0)

            class Meta:
                db_table = "tea_vendors"

    if 'tea_teas' not in tables:
        @migrator.create_model
        class Tea(pw.Model):
            deleted = pw.DateTimeField(null=True)
            description = pw.CharField(max_length=255, null=True)
            illustration = pw.CharField(max_length=255)
            ingredients = pw.TextField(null=True)
            link = pw.CharField(max_length=255)
            long_description = pw.TextField(null=True)
            name = pw.CharField(max_length=255)
            price = pw.FloatField(null=True)
            price_unit = pw.CharField(max_length=255, null=True)
            slug = pw.CharField(max_length=255)
            tips_raw = pw.CharField(max_length=255, null=True)
            tips_duration = pw.IntegerField(null=True)
            tips_mass = pw.IntegerField(null=True)
            tips_temperature = pw.IntegerField(null=True)
            tips_volume = pw.IntegerField(null=True)
            tips_extra = pw.CharField(max_length=255, null=True)
            tips_max_brews = pw.IntegerField(default=1)
            updated = pw.DateTimeField(default=dt.datetime.now)
            vendor = pw.ForeignKeyField(db_column='vendor', rel_model=migrator.orm['tea_vendors'], to_field='id')
            vendor_internal_id = pw.CharField(db_column='vendor_id', max_length=255, null=True)

            class Meta:
                db_table = "tea_teas"

    if 'tea_lists' not in tables:
        @migrator.create_model
        class TeaList(pw.Model):
            name = pw.CharField(max_length=255)
            created_at = pw.DateTimeField(default=dt.datetime.now)
            share_key = pw.CharField(max_length=255, null=True, unique=True)
            cookie_key = pw.CharField(max_length=255, unique=True)
            creator_ip = pw.CharField(max_length=255)
            share_key_valid_until = pw.DateTimeField(null=True)

            class Meta:
                db_table = "tea_lists"

    if 'tea_lists_items' not in tables:
        @migrator.create_model
        class TeaListItem(pw.Model):
            is_empty = pw.IntegerField()
            tea_list = pw.ForeignKeyField(db_column='list_id', rel_model=migrator.orm['tea_lists'], to_field='id')
            tea = pw.ForeignKeyField(db_column='tea_id', rel_model=migrator.orm['tea_teas'], to_field='id')

            class Meta:
                db_table = "tea_lists_items"

    if 'tea_types' not in tables:
        @migrator.create_model
        class TeaType(pw.Model):
            name = pw.CharField(max_length=255, unique=True)
            slug = pw.CharField(max_length=255, unique=True)
            is_origin = pw.BooleanField()
            order = pw.IntegerField(null=True)

            class Meta:
                db_table = "tea_types"

    if 'tea_teas_types' not in tables:
        @migrator.create_model
        class TypeOfATea(pw.Model):
            tea = pw.ForeignKeyField(db_column='tea_id', rel_model=migrator.orm['tea_teas'], to_field='id')
            tea_type = pw.ForeignKeyField(db_column='type_id', rel_model=migrator.orm['tea_types'], to_field='id')

            class Meta:
                db_table = "tea_teas_types"

                primary_key = pw.CompositeKey('tea', 'tea_type')



def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.remove_model('tea_teas_types')
    migrator.remove_model('tea_types')
    migrator.remove_model('tea_lists_items')
    migrator.remove_model('tea_lists')
    migrator.remove_model('tea_teas')
    migrator.remove_model('tea_vendors')
