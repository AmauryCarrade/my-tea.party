from flask import request, render_template, abort
from peewee import SQL, fn
from playhouse.flask_utils import get_object_or_404

from .model import Tea, TeaVendor, TeaType, TypeOfATea
from .teaparty import app


@app.route('/')
def homepage():
    return render_template('index.html')


@app.route('/<tea_vendor>/<tea_slug>')
def tea(tea_vendor, tea_slug):
    tea = get_object_or_404(Tea.select().join(TeaVendor),
                            Tea.slug == tea_slug.strip().lower(),
                            TeaVendor.slug == tea_vendor.strip().lower())

    tea_types = (TeaType.select(TeaType.name, TeaType.slug)
                 .join(TypeOfATea)
                 .where(TypeOfATea.tea == tea)
                 .execute())

    print(tea_types)
    return render_template('tea.html', tea=tea, tea_types=tea_types)
