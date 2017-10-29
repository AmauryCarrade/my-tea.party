from ..teaparty import app
from ..model import pwdb

from .import_teas import *  # noqa
from .generate_thumbnails import *  # noqa

app.cli.add_command(pwdb.cli, 'db')
