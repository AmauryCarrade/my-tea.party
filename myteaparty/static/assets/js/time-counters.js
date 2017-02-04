(function (document)
{
    'use strict';

    function secondsToTimer(seconds)
    {
        var hours   = parseInt(Math.floor(seconds / 3600));
        var minutes = parseInt(Math.floor((seconds - (hours * 3600)) / 60));
        var seconds = parseInt(seconds - (hours * 3600) - (minutes * 60));

        if (hours   < 10) { hours   = "0" + hours;   }
        if (minutes < 10) { minutes = "0" + minutes; }
        if (seconds < 10) { seconds = "0" + seconds; }

        return (hours > 0 ? hours + ':' : '') + minutes + ':' + seconds;
    }

    var progress_buttons = document.getElementsByClassName('button-progress');
    for (var i = 0; i < progress_buttons.length; i++)
    {
        progress_buttons[i].addEventListener('click', function (ev)
        {
            var target = ev.target;
            while (!target.classList.contains('button-progress'))
                target = target.parentElement;

            // Timer already running
            if (target.classList.contains('active')) return;

            // We request notifications permissions here, before use,
            // not directly when the website loads.
            if ("Notification" in window)
                Notification.requestPermission();

            var duration = parseInt(target.dataset.time);
            var started = Date.now();

            var title = target.dataset.name;
            if (!title)
                title = 'My Tea Party';

            var label = target.getElementsByClassName('button-progress-label')[0];
            var bar = target.getElementsByClassName('button-progress-bar')[0];

            target.classList.add('active');

            label.dataset.originalLabel = label.innerHTML;
            label.innerHTML = secondsToTimer(duration);

            bar.style.width = '0%';

            var timer = setInterval(function ()
            {
                var time_left = duration - ((Date.now() - started) / 1000);
                var percentage = ((duration - time_left) / duration) * 100;

                if (time_left <= 0)
                {
                    label.innerHTML = label.dataset.originalLabel;
                    target.classList.remove('active');

                    if ("Notification" in window)
                    {
                        var notification = new Notification(title, {
                            lang: 'fr',
                            body: 'Votre thé est infusé ! Buvez tant que c\'est chaud !',
                            vibrate: [200, 100, 200],
                            // So if the user infuses multiple teas at the same time,
                            // he'll be notified for each of them
                            renotify: true
                        });
                    }

                    clearInterval(timer);
                }
                else
                {
                    label.innerHTML = secondsToTimer(time_left);
                    bar.style.width = percentage + '%';
                }
            }, 100);
        });
    }

})(document);
