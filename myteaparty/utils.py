import os
import requests
import hashlib

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

    file_name = m.hexdigest() + '.'\
                              + (url.split('.')[-1] if '.' in url else '')
    file_dir = os.path.join(app.root_path, 'static',
                            app.config['STATIC_FILES_FOLDER'],
                            file_name[:2])
    file_path = os.path.join(file_dir, file_name)

    os.makedirs(file_dir, exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(file_content)

    return file_name
