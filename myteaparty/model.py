from peewee import MySQLDatabase, Model, CharField, TextField, IntegerField, FloatField, DateTimeField, \
                   BooleanField, ForeignKeyField, CompositeKey
from .teaparty import app

database = MySQLDatabase(app.config['DATABASE_BASE'], **{
    'host': app.config['DATABASE_HOST'],
    'port': app.config['DATABASE_PORT'],
    'user': app.config['DATABASE_USER'],
    'password': app.config['DATABASE_PASS']
})


class UnknownField(object):
    pass


class BaseModel(Model):
    class Meta:
        database = database


class TeaVendor(BaseModel):
    description = CharField()
    link = CharField()
    logo = CharField(null=True)
    name = CharField()
    slug = CharField(unique=True)

    class Meta:
        db_table = 'tea_vendors'
        indexes = (
            (('name', 'link'), True),
        )


class TeaType(BaseModel):
    name = CharField(unique=True)
    slug = CharField(unique=True)
    is_origin = BooleanField()
    order = IntegerField()

    class Meta:
        db_table = 'tea_types'


class Tea(BaseModel):
    deleted = DateTimeField(null=True)
    description = CharField(null=True)
    illustration = CharField()
    ingredients = TextField(null=True)
    link = CharField()
    long_description = TextField(null=True)
    name = CharField()
    price = FloatField(null=True)
    price_unit = CharField(null=True)
    slug = CharField(unique=True)
    tips_raw = CharField(null=True)
    tips_duration = IntegerField(null=True)
    tips_mass = IntegerField(null=True)
    tips_temperature = IntegerField(null=True)
    tips_volume = IntegerField(null=True)
    updated = DateTimeField()
    vendor = ForeignKeyField(db_column='vendor', rel_model=TeaVendor, to_field='id')
    vendor_internal_id = CharField(null=True, db_column='vendor_id')

    class Meta:
        db_table = 'tea_teas'


class TypeOfATea(BaseModel):
    tea = ForeignKeyField(db_column='tea_id', rel_model=Tea, to_field='id')
    tea_type = ForeignKeyField(db_column='type_id', rel_model=TeaType, to_field='id')

    class Meta:
        db_table = 'tea_teas_types'
        primary_key = CompositeKey('tea', 'tea_type')


class TeaList(BaseModel):
    creator_ip = CharField()
    key = CharField(unique=True)

    class Meta:
        db_table = 'tea_lists'


class TeaListItem(BaseModel):
    is_empty = IntegerField()
    tea_list = ForeignKeyField(db_column='list_id', rel_model=TeaList,
                               to_field='id')
    tea = ForeignKeyField(db_column='tea_id', rel_model=Tea, to_field='id')

    class Meta:
        db_table = 'tea_lists_items'
