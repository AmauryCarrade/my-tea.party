# Database connection

DATABASE_HOST = 'localhost'
DATABASE_PORT = 3306
DATABASE_USER = 'root'
DATABASE_PASS = ''
DATABASE_BASE = 'teaparty'


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
