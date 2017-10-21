# Database connection

# See http://docs.peewee-orm.com/en/latest/peewee/database.html#connecting-using-a-database-url
# Warning: search will not work with SQLite as it uses SQL functions not implemented in this driver.
# DATABASE = 'mysql://user:passwd@ip:port/my_db'
DATABASE = ''


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

# The format is (width, height);
# None means don't consider and resize using the other
# respecting proportions
STATIC_FILES_FORMATS = {
	'small': (None, 144),
	'open-graph': (600, None)
}


# Lists

LISTS_DEFAULT_NAME = 'Liste par défaut'


# Cookies

COOKIE_LISTS = 'mtp_tea_lists'
COOKIE_ACTIVE_LIST = 'mtp_tea_active_list'


# A random secret key

SECRET_KEY = 'some random string here'
