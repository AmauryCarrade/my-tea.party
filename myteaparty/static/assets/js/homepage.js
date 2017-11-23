(function()
{
    var lists_handles = document.querySelectorAll('a.teas-list-handle');
    var lists_contents = document.querySelectorAll('.teas-list-content');

    for (var i = lists_handles.length - 1; i >= 0; i--)
    {
        lists_handles[i].onclick = function(e)
        {
            e.preventDefault();

            for (var i = lists_contents.length - 1; i >= 0; i--)
            {
                if (this.dataset.list == lists_contents[i].dataset.list)
                {
                    lists_contents[i].classList.remove('is-hidden');
                }
                else
                {
                    lists_contents[i].classList.add('is-hidden');
                }
            }

            for (var i = lists_handles.length - 1; i >= 0; i--)
            {
                if (this.dataset.list == lists_handles[i].dataset.list)
                {
                    lists_handles[i].classList.add('is-active');
                }
                else
                {
                    lists_handles[i].classList.remove('is-active');
                }
            }

            document.cookie = window.mtp_config['cookies']['last_viewed_list'] + '=' + this.dataset.list;
        };
    }
})();
