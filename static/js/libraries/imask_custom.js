document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-mask]').forEach(function (el) {
    if (window.IMask) {
      const maskPattern = el.dataset.mask;
      const datePatterns = ['00/00/0000', '0000-00-00'];

      const customPlaceholders = {
        '0 0 0 0 0':            { mask: '0 0 0 0 0',            blocks: { 0: null }, hint: '1 0 2 8 1' },
        '(+63)900-000-0000':    { hint: '(+63)912-345-6789' },
        '000-000-000':          { hint: '123-456-789' },
        '00-0000000-0':         { hint: '12-3456789-0' },
        '00-000000000-0':       { hint: '12-345678901-2' },
        '0000-0000-0000':       { hint: '1234-5556-7890' },
      };

      if (datePatterns.includes(maskPattern)) {
        const maskInstance = IMask(el, {
          mask: Date,
          pattern: 'm/`d/`Y',
          lazy: false,
          format: function (date) {
            const mm = String(date.getMonth() + 1).padStart(2, '0');
            const dd = String(date.getDate()).padStart(2, '0');
            const yyyy = date.getFullYear();
            return `${mm}/${dd}/${yyyy}`;
          },
          parse: function (str) {
            const [mm, dd, yyyy] = str.split('/');
            return new Date(yyyy, mm - 1, dd);
          },
          blocks: {
            m: { mask: IMask.MaskedRange, from: 1, to: 12, maxLength: 2, placeholderChar: 'm' },
            d: { mask: IMask.MaskedRange, from: 1, to: 31, maxLength: 2, placeholderChar: 'd' },
            Y: { mask: IMask.MaskedRange, from: 1900, to: 2100, placeholderChar: 'y' },
          }
        });

        const placeholderColor = '#9CA3AF';
        el.style.color = placeholderColor;
        maskInstance.on('accept', function () {
          el.style.color = maskInstance.value === '' ? placeholderColor : 'var(--tblr-body-color)';
        });

      } else if (customPlaceholders[maskPattern]) {
        const hint = customPlaceholders[maskPattern].hint;
        el.placeholder = hint;
        el.style.color = '#9CA3AF';

        const maskInstance = IMask(el, {
          mask: maskPattern,
          lazy: true,
        });

        maskInstance.on('accept', function () {
          el.style.color = maskInstance.value === '' ? '#9CA3AF' : 'var(--tblr-body-color)';
        });

      } 

      else {
        const maskInstance = IMask(el, {
          mask: maskPattern,
          lazy: false,
          placeholderChar: '_'
        });

        const placeholderColor = '#9CA3AF';
        el.style.color = placeholderColor;
        maskInstance.on('accept', function () {
          el.style.color = maskInstance.value === '' ? placeholderColor : 'var(--tblr-body-color)';
        });
      }
    }
  });
});