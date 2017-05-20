# Database connection

# See http://docs.peewee-orm.com/en/latest/peewee/database.html#connecting-using-a-database-url
# Warning: search will not work with SQLite as it uses SQL functions not implemented in this driver.
DATABASE = 'mysql://user:passwd@ip:port/my_db'


# Search options

# The weight of the fields when searching for a tea using keywords.
SEARCH_WEIGHTS = {
    'name': 20,
    'desc': 10,
    'ldesc': 5
}

ITEMS_PER_PAGE = 12


# Static files storage

STATIC_FILES_FOLDER = 'r'


# A random secret key

SECRET_KEY = 'some random string here'
