import random
import uuid

from datetime import datetime, timedelta
from flask import jsonify, request, redirect, url_for, render_template, abort
from playhouse.flask_utils import get_object_or_404

from ..model import Tea, TeaList, TeaListItem
from ..teaparty import app
from ..utils import after_request


_cookies_properties = {
    'expires': datetime.now() + timedelta(days=366 * 84),
    'max_age': int(timedelta(days=366 * 84).total_seconds())
}


def create_tea_list(name=None):
    '''
    Creates a new teas list, with the provided name or a default one.
    '''
    return TeaList.create(
        name=name or app.config['LISTS_DEFAULT_NAME'],
        cookie_key=str(uuid.uuid4().hex).upper().replace('-', ''),
        creator_ip=request.remote_addr
    )


def add_to_list(tea_list, tea):
    '''
    Adds a tea to a list. Returns the new list item model instance.
    '''
    item, _ = TeaListItem.get_or_create(
        tea=tea,
        tea_list=tea_list,
        defaults={'is_empty': False}
    )

    return item


def remove_from_list(tea_list, tea):
    '''
    Removes a tea from a list.
    '''
    TeaListItem.delete().where((TeaListItem.tea_list == tea_list) & (TeaListItem.tea == tea)).execute()


def set_empty_in_list(tea_list, tea, empty=None):
    '''
    Marks a tea as empty in a list.

    empty: if None, toggles the value. Else (True/False) sets the given value.
    '''
    try:
        item = TeaListItem.get(tea_list=tea_list, tea=tea)
    except TeaListItem.DoesNotExist:
        return

    empty_value = empty
    if empty is None:
        empty_value = not item.is_empty

    item.is_empty = empty_value
    item.save()


def set_active_list(response, active_list):
    '''
    Sets the cookies to refer the active list.
    '''
    response.set_cookie(app.config['COOKIE_ACTIVE_LIST'], active_list.cookie_key, **_cookies_properties)
    add_to_registered_lists(response, active_list)


def add_to_registered_lists(response, tea_list):
    '''
    Adds the given list to the user's registered lists in his browser.
    '''
    registered_lists = [i for i in request.cookies.get(app.config['COOKIE_LISTS'], '').split('|') if i]
    if tea_list.cookie_key not in registered_lists:
        registered_lists.append(tea_list.cookie_key)
        response.set_cookie(app.config['COOKIE_LISTS'], '|'.join(registered_lists), **_cookies_properties)


def _gen_list_share_key():
    '''
    Generates a sharing key (6-digits key) for the list.
    The key is checked to be unique.
    '''
    keys = [tea_list.share_key for tea_list in TeaList.select(TeaList.share_key) if tea_list.share_key is not None]
    share_key = None

    while share_key is None or share_key in keys:
        share_key = random.randint(100000, 999999)

    return share_key


def get_tea_lists_from_request():
    '''
    Returns all the user's registered lists.
    '''
    registered_lists = [i for i in request.cookies.get(app.config['COOKIE_LISTS'], '').split('|') if i]
    return TeaList.select().where(TeaList.cookie_key << registered_lists)


def is_list_registered_for_user(tea_list):
    '''
    Checks if the given list is registered for this user.
    '''
    return any([tea_list.id == user_list.id for user_list in get_tea_lists_from_request()])


def get_tea_list_from_request(create=True):
    '''
    Returns the user's active list. Returns None if there is none.
    '''
    active_list_id = request.cookies.get(app.config['COOKIE_ACTIVE_LIST'])
    active_list = None

    if active_list_id:
        try:
            active_list = TeaList.get(TeaList.cookie_key == active_list_id)
        except TeaList.DoesNotExist:
            active_list = None

    if not active_list and create:
        active_list = create_tea_list()

        @after_request
        def set_active_cookie(response):
            set_active_list(response, active_list)

    return active_list


def is_tea_in_active_list(tea):
    '''
    Checks if the given tea is in the user's active list (if there is any).
    '''
    # This is checked on every tea page, so if there is no list,
    # we don't want to create one. Just to check if it's in the list
    # if it exists.
    active_list = get_tea_list_from_request(create=False)
    if not active_list:
        return False

    return (TeaListItem.select()
                       .where((TeaListItem.tea_list == active_list) & (TeaListItem.tea == tea))
                       .exists())


def get_teas_in_list(teas_list, limit=None):
    '''
    Returns the teas in the given list.
    If limit is given and not None, returns a tuple with the list and the total count
    '''
    req = (TeaListItem.select()
               .join(TeaList)
               .join(Tea, on=Tea.id == TeaListItem.tea)
               .where(TeaList.id == teas_list.id))

    if limit is None:
        return req

    req = req.limit(limit)
    count = (TeaListItem.select()
               .join(TeaList)
               .join(Tea, on=Tea.id == TeaListItem.tea)
               .where(TeaList.id == teas_list.id)
               .count())

    return req, count


def get_teas_in_active_list():
    '''
    Returns the teas in the user's active list.
    '''
    active_list = get_tea_list_from_request(create=False)
    if not active_list:
        return []

    return get_teas_in_list(active_list)


def _handle_response(tea):
    '''
    Handles the response of an API call for tea lists endpoints.
    '''
    if request.method == 'GET':
        if 'next' in request.args:
            return redirect(request.args.get('next'))
        else:
            return redirect(url_for('tea', tea_vendor=tea.vendor.slug, tea_slug=tea.slug))
    else:
        return jsonify({'result': 'ok'})


@app.route('/lists/active', methods=['PUT'])
@app.route('/lists/active/add')
def add_tea_to_list():
    tea = get_object_or_404(Tea, Tea.id == request.args.get('tea_id', type=int))
    add_to_list(get_tea_list_from_request(), tea)

    return _handle_response(tea)


@app.route('/lists/active', methods=['DELETE'])
@app.route('/lists/active/remove')
def remove_tea_from_list():
    tea = get_object_or_404(Tea, Tea.id == request.args.get('tea_id', type=int))
    remove_from_list(get_tea_list_from_request(), tea)

    return _handle_response(tea)


@app.route('/lists/active/toggle_empty')
def toggle_empty_tea_in_list():
    tea = get_object_or_404(Tea, Tea.id == request.args.get('tea_id', type=int))
    set_empty_in_list(get_tea_list_from_request(), tea)

    return _handle_response(tea)


@app.route('/sync')
def sync_list():
    active_list = get_tea_list_from_request()
    now = datetime.now()

    if ('regen' in request.args
            or active_list.share_key is None
            or active_list.share_key_valid_until is None
            or active_list.share_key_valid_until < now):
        active_list.share_key = _gen_list_share_key()
        active_list.share_key_valid_until = now + timedelta(hours=app.config['SHARE_KEY_EXPIRES_AFTER'])
        active_list.save()

    return render_template('sync.html', active_list=active_list)


@app.route('/s/<share_key>')
def sync_list_newdevice(share_key):
    try:
        new_list = (TeaList.select()
                           .where((TeaList.share_key == share_key) & (TeaList.share_key_valid_until > datetime.now()))
                           .get())
    except TeaList.DoesNotExist:
        abort(404)

    if 'confirm' in request.args:
        @after_request
        def set_active_cookie(response):
            set_active_list(response, new_list)

        return render_template('sync_newdevice.html', new_list=new_list, done=True)

    elif is_list_registered_for_user(new_list):
        return render_template('sync_newdevice.html',
                               new_list=new_list,
                               done=False,
                               already_registered=True,
                               already_registered_and_active=get_tea_list_from_request().id == new_list.id)

    new_list_teas_sample, new_list_teas_count = get_teas_in_list(new_list, limit=5)

    return render_template('sync_newdevice.html',
       new_list=new_list,
       tea_sample=new_list_teas_sample,
       teas_count=new_list_teas_count,
       done=False,
       already_registered=False
    )
