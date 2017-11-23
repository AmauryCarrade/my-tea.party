/**
 * method -> GET, POST…
 * url
 * onsuccess(request, json_data)
 * onerror(request, is_connection_error)
 */
function ajax_json_call(method, url, onsuccess, onerror)
{
    'use strict';

    var request = new XMLHttpRequest();
    request.open(method, url, true);

    if (method.toUpperCase() == 'POST')
    {
        request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
    }

    request.onload = function()
    {
      if (this.status >= 200 && this.status < 400)
      {
        // Success!
        var data = JSON.parse(this.response);
        onsuccess(this, data);
      }
      else
      {
        onerror(this, false);
      }
    };

    request.onerror = function() {
        onerror(this, true)
    };

    request.send();
}
