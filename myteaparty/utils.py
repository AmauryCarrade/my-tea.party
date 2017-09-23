import hashlib
import os
import requests
import shutil

from flask import request, url_for
from path import Path
from PIL import Image
from werkzeug import url_encode
from .teaparty import app


def save_distant_file(url):
    """
    Saves the file at the given URL and returns an identifier for this
    file.
    """
    r = requests.get(url)
    if not r.ok:
        return None

    file_content = r.content

    m = hashlib.sha256()
    m.update(file_content)

    _, ext = os.path.splitext(url)

    file_name = f'{m.hexdigest()}{ext}'
    file_dir = Path(app.root_path) / 'static' / app.config['STATIC_FILES_FOLDER'] / file_name[:2]
    file_path = file_dir / file_name

    file_dir.makedirs_p()
    file_path.write_bytes(file_content)

    generate_thumbnails(file_path)

    return file_name

def generate_thumbnails(file_path):
    '''
    Generates thumbnails for the given filename
    '''
    if app.config['STATIC_FILES_FORMATS']:
        infinity = float('+inf')

        for thumb_name, thumb_format in app.config['STATIC_FILES_FORMATS'].items():
            x, y = thumb_format
            if x is None: x = infinity
            if y is None: y = infinity

            thumb_path = get_external_filename(file_path, thumb_name)

            try:
                image = Image.open(file_path)
                image.thumbnail((x, y))
                image.save(thumb_path)
            except:
                shutil.copy(file_path, thumb_path)

            x, y = 2*x, 2*y
            thumb_path = get_external_filename(file_path, thumb_name + '@2x')

            try:
                image = Image.open(file_path)
                image.thumbnail((x, y))
                image.save(thumb_path)
            except:
                shutil.copy(file_path, thumb_path)

def get_external_filename(file_name, file_format=None):
    '''
    Returns the filesystem file name for the given format.
    The file name is returned as-is without format.
    '''
    if file_format is not None:
        name, ext = os.path.splitext(file_name)
        file_name = f'{name}-{file_format}{ext}'

    return file_name

def is_post_processed_file(file_name):
    '''
    Checks if the given file is a post-processed file or an
    original file.
    '''
    name, _ = os.path.splitext(file_name)
    formats = list(app.config['STATIC_FILES_FORMATS'].keys())
    formats += [format + '@2x' for format in formats]

    return any([name.endswith(file_format) for file_format in formats])


@app.template_global()
def update_query(**new_values):
    """
    Modifies and returns the current page's query string
    by adding or replacing the given values.
    """
    args = request.args.copy()

    for key, value in new_values.items():
        args[key] = value

    return '{}?{}'.format(request.path, url_encode(args))

@app.template_global()
def external(file_name, file_format=None, absolute=False):
    file_name = get_external_filename(file_name, file_format)
    return url_for('static', filename=f'{app.config["STATIC_FILES_FOLDER"]}/{file_name[0:2]}/{file_name}', _external=absolute)
