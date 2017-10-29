import click

from path import Path

from ..teaparty import app
from ..utils import generate_thumbnails, get_external_filename, is_post_processed_file


@app.cli.command('generate-thumbnails')
@click.option('--regenerate',
              is_flag=True,
              default=False,
              help='If specified, existing thumbnails will be re-genered')
@click.option('--directory',
              default=Path(app.root_path) / 'static' / app.config['STATIC_FILES_FOLDER'],
              show_default=True,
              help='The root directory where files are stored')
def generate_thumbnails_command(regenerate, directory):
    '''
    (Re)Generates the thumbnails.
    '''
    directory = Path(directory)
    if not directory.exists():
        click.echo('Directory does not exists. Exiting.', err=True)
        return

    formats = list(app.config['STATIC_FILES_FORMATS'].keys())
    formats += [format + '@2x' for format in formats]

    for file in directory.walkfiles():
        if is_post_processed_file(file):
            continue

        file_dir = file.dirname()
        files_all_ok = all([(file_dir / get_external_filename(file, file_format)).exists() for file_format in formats])

        if not files_all_ok or regenerate:
            click.echo(f'Generating thumbnails for {file.name}…{" [regenerated]" if regenerate else ""}')
            generate_thumbnails(file)

    click.echo('Done.')
