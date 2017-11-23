import random
import uuid

from datetime import datetime, timedelta
from flask import jsonify, request, redirect, url_for, render_template, abort
from peewee import fn
from playhouse.flask_utils import get_object_or_404

from ..model import Tea, TeaList, TeaListItem
from ..teaparty import app
from ..utils import after_request


_cookies_properties = {
    'expires': datetime.now() + timedelta(days=366 * 84),
    'max_age': int(timedelta(days=366 * 84).total_seconds())
}


def create_tea_list(name=None, is_favorites=False):
    '''
    Creates a new teas list, with the provided name or a default one.
    '''
    return TeaList.create(
        name=name or app.config['LISTS_DEFAULT_NAME'],
        cookie_key=str(uuid.uuid4().hex).upper().replace('-', ''),
        creator_ip=request.remote_addr,
        is_favorites=is_favorites
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


def set_favorites_list(response, favorites_list):
    '''
    Sets the cookies to refer the favorites list.
    '''
    response.set_cookie(app.config['COOKIE_FAVORITES_LIST'], favorites_list.cookie_key, **_cookies_properties)


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
    return [tl for tl in TeaList.select().where(TeaList.cookie_key << registered_lists)]


def get_tea_list_from_cookie_key(cookie_key, create=True, abort_if_not_found=True):
    '''
    Returns an user's list from its cookie key (UUID).
    If the cookie key is 'favorites', gets or creates (if create=True) the favorites list.
    Returns None if the list does not exists, or aborts to a 404 error.
    '''
    if cookie_key == 'favorites':
        return get_favorites_list_from_request(create=create)
    else:
        try:
            return TeaList.select().where(TeaList.cookie_key == cookie_key).get()
        except TeaList.DoesNotExist:
            if abort_if_not_found:
                abort(404)
            else:
                return None


def is_list_registered_for_user(tea_list):
    '''
    Checks if the given list is registered for this user.
    '''
    return any([tea_list.id == user_list.id for user_list in get_tea_lists_from_request()])


def get_favorites_list_from_request(create=True):
    '''
    Returns the user's active list. Returns None if there is none.
    '''
    favorites_list_id = request.cookies.get(app.config['COOKIE_FAVORITES_LIST'])
    favorites_list = None

    if favorites_list_id:
        try:
            favorites_list = TeaList.get(TeaList.cookie_key == favorites_list_id)
        except TeaList.DoesNotExist:
            favorites_list = None

    if not favorites_list and create:
        favorites_list = create_tea_list(name=app.config['LISTS_FAVORITES_NAME'], is_favorites=True)

        @after_request
        def set_favorite_cookie(response):
            set_favorites_list(response, favorites_list)

    # If someone tries to manipulate the cookies to put a normal list
    # into the favs cookie
    if favorites_list is not None and not favorites_list.is_favorites:
        favorites_list.is_favorites = True
        favorites_list.save()

    return favorites_list


def is_tea_in_list(tea_list, tea):
    '''
    Checks if the given tea is in the given list.
    '''
    return (TeaListItem.select()
                       .where((TeaListItem.tea_list == tea_list) & (TeaListItem.tea == tea))
                       .exists())


def is_tea_in_favorites_list(tea):
    '''
    Checks if the given tea is in the user's active list (if there is any).
    '''
    # This is checked on every tea page, so if there is no list,
    # we don't want to create one. Just to check if it's in the list
    # if it exists.
    favorites_list = get_favorites_list_from_request(create=False)
    if not favorites_list:
        return False

    return is_tea_in_list(favorites_list, tea)


def get_lists_containing_tea(tea_lists, tea):
    '''
    Checks if the tea is in the given lists.
    Returns a list of the lists where the tea is into.
    '''
    return (
        TeaList
            .select()
            .where(
                (TeaList.id << [tea_list.id for tea_list in tea_lists]) &
                fn.Exists(
                    TeaListItem
                        .select(TeaListItem.id)
                        .join(Tea, on=TeaListItem.tea_id == Tea.id)
                        .where((Tea.id == tea.id) & (TeaList.id == TeaListItem.tea_list))
                )
            )
    )


def get_teas_in_list(tea_list, limit=None):
    '''
    Returns the teas in the given list.
    If limit is given and not None, returns a tuple with the list and the total count
    '''
    req = (TeaListItem.select()
               .join(TeaList)
               .join(Tea, on=Tea.id == TeaListItem.tea)
               .where(TeaList.id == tea_list.id))

    if limit is None:
        return req

    req = req.limit(limit)
    count = (TeaListItem.select()
               .join(TeaList)
               .join(Tea, on=Tea.id == TeaListItem.tea)
               .where(TeaList.id == tea_list.id)
               .count())

    return req, count


def get_teas_in_favorites_list():
    '''
    Returns the teas in the user's active list.
    '''
    favorites_list = get_favorites_list_from_request(create=False)
    if not favorites_list:
        return []

    return get_teas_in_list(favorites_list)


def get_last_viewed_list_key():
    '''
    Returns the key of the last-viewed list on the homepage, to restaure the
    same state when the page is reloaded.
    '''
    return request.cookies.get(app.config['COOKIE_LAST_VIEWED_LIST'], '')

def update_last_viewed_list_key(last_viewed_list):
    '''
    Updates the last-viewed list in the cookie.
    This is only used for the no-javascript fallback.
    '''
    @after_request
    def update_last_viewed_list_key_cookie(response):
        response.set_cookie(app.config['COOKIE_LAST_VIEWED_LIST'], last_viewed_list.cookie_key, **_cookies_properties)


def _handle_response(tea, **kwargs):
    '''
    Handles the response of an API call for tea lists endpoints.
    Keyword arguments are passed to the JSON response for AJAX calls.
    '''
    if request.method == 'GET':
        if 'next' in request.args:
            return redirect(request.args.get('next'))
        else:
            return redirect(url_for('tea', tea_vendor=tea.vendor.slug, tea_slug=tea.slug))
    else:
        res = {'result': 'ok'}
        res.update(kwargs)
        return jsonify(res)


@app.route('/lists/<cookie_key>/add/<int:tea_id>', methods=['GET', 'POST'])
def add_tea_to_list(cookie_key, tea_id):
    tea = get_object_or_404(Tea, Tea.id == tea_id)
    add_to_list(get_tea_list_from_cookie_key(cookie_key), tea)

    return _handle_response(tea, in_list=True)


@app.route('/lists/<cookie_key>/remove/<int:tea_id>', methods=['GET', 'POST'])
def remove_tea_from_list(cookie_key, tea_id):
    tea = get_object_or_404(Tea, Tea.id == tea_id)
    remove_from_list(get_tea_list_from_cookie_key(cookie_key), tea)

    return _handle_response(tea, in_list=True)

@app.route('/lists/<cookie_key>/toggle/<int:tea_id>', methods=['GET', 'POST'])
def toggle_tea_in_list(cookie_key, tea_id):
    tea = get_object_or_404(Tea, Tea.id == tea_id)
    tea_list = get_tea_list_from_cookie_key(cookie_key)
    in_list = None

    if is_tea_in_list(tea_list, tea):
        remove_from_list(tea_list, tea)
        in_list = False
    else:
        add_to_list(tea_list, tea)
        in_list = True

    return _handle_response(tea, in_list=in_list)

@app.route('/lists/create_and_add/<int:tea_id>', methods=['GET', 'POST'])
def create_and_add_to_list(tea_id):
    tea = get_object_or_404(Tea, Tea.id == tea_id)
    tea_list = create_tea_list(name=request.args.get('name', None))

    add_to_list(tea_list, tea)

    @after_request
    def register_the_new_list(response):
        add_to_registered_lists(response, tea_list)

    return _handle_response(
        tea,
        in_list=True,
        list_name=tea_list.name,
        list_cookie_key=tea_list.cookie_key,
        tea_id=tea_id
    )


@app.route('/lists/<cookie_key>/toggle_empty/<int:tea_id>', methods=['GET', 'POST'])
def toggle_empty_tea_in_list(cookie_key, tea_id):
    tea = get_object_or_404(Tea, Tea.id == tea_id)
    set_empty_in_list(get_tea_list_from_cookie_key(cookie_key), tea)

    return _handle_response(tea)


@app.route('/lists/switch_last_viewed/<cookie_key>')
def switch_last_viewed_list(cookie_key):
    update_last_viewed_list_key(get_tea_list_from_cookie_key(cookie_key))

    return redirect(url_for('homepage'))


# TODO BELOW - switch to multi-lists
@app.route('/sync')
def sync_list():
    tea_lists = get_tea_lists_from_request()
    tea_favorites_list = get_favorites_list_from_request()
    all_lists = tea_lists + [tea_favorites_list]

    now = datetime.now()

    for tea_list in all_lists:
        if (('regen' in request.args and (not 'list' in request.args or request.args.get('list') == tea_list.cookie_key))
                or tea_list.share_key is None
                or tea_list.share_key_valid_until is None
                or tea_list.share_key_valid_until < now):
            tea_list.share_key = _gen_list_share_key()
            tea_list.share_key_valid_until = now + timedelta(hours=app.config['SHARE_KEY_EXPIRES_AFTER'])
            tea_list.save()

    return render_template(
        'sync.html',
        tea_lists=tea_lists,
        tea_favorites_list=tea_favorites_list
    )


@app.route('/s/<share_key>')
def sync_list_newdevice(share_key):
    try:
        new_list = (TeaList.select()
                           .where((TeaList.share_key == share_key) & (TeaList.share_key_valid_until > datetime.now()))
                           .get())
    except TeaList.DoesNotExist:
        abort(404)

    is_registered = is_list_registered_for_user(new_list)
    if not is_registered:
        is_registered = get_favorites_list_from_request(create=False) == new_list

    if 'confirm' in request.args and not is_registered:
        register_method = add_to_registered_lists

        is_favorites = new_list.is_favorites
        replace_favorites = request.args.get('replace_favorites', 'True').lower() != 'false'

        if is_favorites and replace_favorites:
            register_method = set_favorites_list

        @after_request
        def set_active_cookie(response):
            register_method(response, new_list)

        return render_template('sync_newdevice.html', new_list=new_list, done=True)

    elif is_registered:
        return render_template(
            'sync_newdevice.html',
            new_list=new_list,
            done=False,
            already_registered=True
        )

    new_list_teas_sample, new_list_teas_count = get_teas_in_list(new_list, limit=5)

    return render_template(
        'sync_newdevice.html',
        new_list=new_list,
        tea_sample=new_list_teas_sample,
        teas_count=new_list_teas_count,
        done=False,
        already_registered=False,
        current_favorites_list=get_favorites_list_from_request(create=False)
    )
