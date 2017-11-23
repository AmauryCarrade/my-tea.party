# Database connection

# See http://docs.peewee-orm.com/en/latest/peewee/database.html#connecting-using-a-database-url
# Warning: search will not work with SQLite as it uses SQL functions not implemented in this driver.
# DATABASE = 'mysql://user:passwd@ip:port/my_db'
DATABASE = ''

# Connection params (for example for pgsql: { encoding: 'utf-8' })
DATABASE_CONNECTION_PARAMS = {}


# Importers

TEA_IMPORTERS_PACKAGE = 'myteaparty.commands.tea_importers'


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

# The format is (width, height);
# None means don't consider and resize using the other
# respecting proportions
STATIC_FILES_FORMATS = {
    'small': (None, 144),
    'open-graph': (600, None)
}


# Lists

LISTS_DEFAULT_NAME = 'Liste par défaut'
LISTS_FAVORITES_NAME = 'Favoris'
SHARE_KEY_EXPIRES_AFTER = 1  # In hours


# Cookies

COOKIE_LISTS = 'mtp_tea_lists'
COOKIE_FAVORITES_LIST = 'mtp_tea_favorites_list'
COOKIE_LAST_VIEWED_LIST = 'mtp_tea_last_viewed_list'


# A random secret key

SECRET_KEY = 'some random string here'


# Debug toolbar

DEBUG_TB_PANELS = [
    'flask_debugtoolbar.panels.versions.VersionDebugPanel',
    'flask_debugtoolbar.panels.timer.TimerDebugPanel',
    'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
    'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
    'flask_debugtoolbar.panels.template.TemplateDebugPanel',
#   'flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel',
#   'flask_pw.debugtoolbar.PeeweeDebugPanel',
    'myteaparty.utils.PeeweeDebugPanel',
    'flask_debugtoolbar.panels.logger.LoggingPanel',
    'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
]
