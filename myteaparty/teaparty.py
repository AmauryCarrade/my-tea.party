import os
import requests
import uuid
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

app = Flask(__name__)
app.config.from_pyfile(os.path.join(app.root_path, 'config.py'))
app.config.from_envvar('TEA_PARTY_SETTINGS', silent=True)

from .model import Tea, TeaVendor, TeaList, TeaListItem, database
from .utils import *
from .commands import *
