(function() {
    'use strict';
    var handles = document.getElementsByClassName('sync-url-handle');

    for (var i = handles.length - 1; i >= 0; i--)
    {
        handles[i].addEventListener('click', function (e)
        {
            var copyBuffer = document.body.appendChild(document.createElement('textarea'));
            var originalTooltip = this.getAttribute('data-tooltip');

            self = this;

            copyBuffer.className = 'copy-buffer';
            copyBuffer.value = this.children[0].textContent;
            copyBuffer.select();

            try
            {
                if (!document.execCommand('copy'))
                {
                    console.error('Copy failed.');
                    this.setAttribute('data-tooltip', 'Erreur lors de la copie');
                }
                else
                {
                    this.setAttribute('data-tooltip', 'Lien copié !');
                }
            }
            catch(e)
            {
                console.error('Error while executing copy command: %o', e);
                this.setAttribute('data-tooltip', 'Erreur lors de la copie');
            }

            if (this.timeoutId) clearTimeout(this.timeoutId);

            this.timeoutId = setTimeout(function ()
            {
                self.setAttribute('data-tooltip', originalTooltip);
            }, 2000);

            document.body.removeChild(copyBuffer);
        });
    }
})();
