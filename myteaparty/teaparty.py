import os
from flask import Flask

app = Flask(__name__)
app.config.from_pyfile(os.path.join(app.root_path, 'config.py'))
app.config.from_envvar('TEA_PARTY_SETTINGS', silent=True)

from .commands import *  # noqa
