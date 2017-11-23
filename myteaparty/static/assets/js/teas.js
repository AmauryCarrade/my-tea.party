(function()
{
    'use strict';

    var tea_lists_opener = document.getElementById('open-modal-lists');
    var tea_lists_closer = document.querySelectorAll('.modal-close, .modal-background, .modal-lists-close');
    var tea_lists_modal  = document.getElementById('modal-lists');

    tea_lists_opener.onclick = function(e)
    {
        tea_lists_modal.classList.add('is-active');
        e.preventDefault();
    };

    for (var i = tea_lists_closer.length - 1; i >= 0; i--)
    {
        tea_lists_closer[i].onclick = function(e)
        {
            tea_lists_modal.classList.remove('is-active');
            e.preventDefault();
        };
    }

    var tea_lists_togglers = document.querySelectorAll('.toggle-list-link');

    for (var i = tea_lists_togglers.length - 1; i >= 0; i--)
    {
        tea_lists_togglers[i].onclick = function(e)
        {
            e.preventDefault();

            self = this;

            var icon = self.querySelectorAll('span.fa')[0];
            var was_unchecked = icon.classList.contains('list-unchecked');

            icon.classList.remove('fa-check', 'list-unchecked');
            icon.classList.add('fa-circle-o-notch', 'fa-spin');

            ajax_json_call(
                'POST',
                this.href,
                function(request, data)
                {
                    icon.classList.remove('fa-circle-o-notch', 'fa-spin');
                    icon.classList.add('fa-check');

                    if (!data.in_list)
                    {
                        icon.classList.add('list-unchecked');
                    }
                },
                function(request, is_connection_error)
                {
                    icon.classList.remove('fa-circle-o-notch', 'fa-spin');
                    icon.classList.add('fa-warning');

                    self.classList.add('is-error');

                    self.setAttribute('title', 'Impossible d\'ajouter le thé à cette liste.' + (is_connection_error ? ' Il semblerait que vous ne soyez plus connecté à internet.' : ''));

                    setTimeout(function() {
                        self.classList.remove('is-error');
                        icon.classList.remove('fa-warning');
                        icon.classList.add('fa-check');

                        if (was_unchecked)
                        {
                            icon.classList.add('list-unchecked');
                        }
                    }, 1500);
                }
            );
        };
    }
})();
