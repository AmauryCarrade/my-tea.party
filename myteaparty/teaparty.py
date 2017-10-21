import os
from flask import Flask

app = Flask(__name__)
app.config.from_pyfile(os.path.join(app.root_path, 'config.py'))
app.config.from_envvar('TEA_PARTY_SETTINGS', silent=True)

from .model import database  # noqa

@app.teardown_request
def _db_close(exc):
    if not database.is_closed():
        database.close()

from .commands import *  # noqa
from .views.teas import *  # noqa
from .views.lists import *  # noqa
