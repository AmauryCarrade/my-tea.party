import datetime

from flask_pw import Peewee
from path import Path
from peewee import Model, CharField, TextField, IntegerField, FloatField, DateTimeField, \
                   BooleanField, ForeignKeyField, CompositeKey, SqliteDatabase
from playhouse.db_url import connect

from .teaparty import app


app.config['PEEWEE_DATABASE_URI'] = app.config['DATABASE'] or 'sqlite:///myteaparty.sqlite'
app.config['PEEWEE_CONNECTION_PARAMS'] = app.config['DATABASE_CONNECTION_PARAMS'] or {}
app.config['PEEWEE_MODELS_MODULE'] = 'myteaparty.model'

app.config['PEEWEE_MIGRATE_TABLE'] = 'tea_migrations_history'
app.config['PEEWEE_MIGRATE_DIR'] = Path(app.root_path) / 'migrations'

pwdb = Peewee(app)

database = pwdb.database


class UnknownField(object):
    pass


BaseModel = pwdb.Model


class TeaVendor(BaseModel):
    description = CharField()
    link = CharField()
    logo = CharField(null=True)
    name = CharField()
    twitter = CharField(null=True)
    slug = CharField(unique=True)
    order = IntegerField(default=0)

    class Meta:
        db_table = 'tea_vendors'
        indexes = (
            (('name', 'link'), True),
        )


class TeaType(BaseModel):
    name = CharField(unique=True)
    slug = CharField(unique=True)
    is_origin = BooleanField()
    order = IntegerField(null=True)

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
    slug = CharField()
    tips_raw = CharField(null=True)
    tips_duration = IntegerField(null=True)
    tips_mass = IntegerField(null=True)
    tips_temperature = IntegerField(null=True)
    tips_volume = IntegerField(null=True)
    tips_extra = CharField(null=True)
    tips_max_brews = IntegerField(default=1)
    updated = DateTimeField(default=datetime.datetime.now)
    vendor = ForeignKeyField(db_column='vendor', rel_model=TeaVendor, to_field='id')
    vendor_internal_id = CharField(null=True, db_column='vendor_id')

    class Meta:
        db_table = 'tea_teas'
        indexes = (
            (('slug', 'vendor'), True),  # Trailing comma (tuple)
        )


class TypeOfATea(BaseModel):
    tea = ForeignKeyField(db_column='tea_id', rel_model=Tea, to_field='id')
    tea_type = ForeignKeyField(db_column='type_id', rel_model=TeaType, to_field='id')

    class Meta:
        db_table = 'tea_teas_types'
        primary_key = CompositeKey('tea', 'tea_type')


class TeaList(BaseModel):
    name = CharField()
    is_favorites = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)
    share_key = CharField(unique=True, null=True, default=None)
    cookie_key = CharField(unique=True)
    creator_ip = CharField()
    share_key_valid_until = DateTimeField(null=True)

    def __iter__(self):
        '''
        We can iter over a TeaList model object to
        get the teas inside.

        for tea in teas_list:
            ...
        '''
        teas_in_list = (
            TeaListItem
                .select()
                .join(TeaList)
                .join(Tea, on=Tea.id == TeaListItem.tea)
                .where(TeaList.id == self.id)
        )

        for tea in teas_in_list:
            yield tea

    def __bool__(self):
        '''
        Truthy value if the list is not empty
        '''
        return TeaListItem.select().where(TeaListItem.tea_list == self).exists()

    class Meta:
        db_table = 'tea_lists'


class TeaListItem(BaseModel):
    is_empty = IntegerField()
    tea_list = ForeignKeyField(db_column='list_id', rel_model=TeaList,
                               to_field='id')
    tea = ForeignKeyField(db_column='tea_id', rel_model=Tea, to_field='id')

    class Meta:
        db_table = 'tea_lists_items'


def init_db():
    """
    Utility to initialize an empty database, meant to be used from
    Flask shell.
    """
    database.create_tables([TeaVendor, TeaType, Tea, TypeOfATea, TeaList, TeaListItem])


def get_or_create(Model, **kwargs):
    '''
    A get_or_create method exactly like the peewee's one, but compatible with
    SQLite (does not starts a transaction if SQLite is used because it does not
    support nested transactions).
    '''
    defaults = kwargs.pop('defaults', {})
    query = Model.select()
    for field, value in kwargs.items():
        if '__' in field:
            query = query.filter(**{field: value})
        else:
            query = query.where(getattr(Model, field) == value)

    try:
        return query.get(), False
    except Model.DoesNotExist:
        try:
            params = dict((k, v) for k, v in kwargs.items()
                          if '__' not in k)
            params.update(defaults)

            if type(Model._meta.database) == SqliteDatabase:
                return Model.create(**params), True
            else:
                with Model._meta.database.atomic():
                    return Model.create(**params), True
        except IntegrityError as exc:
            try:
                return query.get(), False
            except Model.DoesNotExist:
                raise exc
