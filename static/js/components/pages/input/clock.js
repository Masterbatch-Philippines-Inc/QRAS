// datetime.js
function updateClock() {
  const offset = (window.CLOCK_OFFSET_MINUTES || 0) * 60 * 1000;
  const now = new Date(Date.now() - offset);
  const rawHrs = now.getHours();
  const h      = String(rawHrs % 12 || 12).padStart(2, '0');
  const m      = String(now.getMinutes()).padStart(2, '0');
  const s      = String(now.getSeconds()).padStart(2, '0');

  document.getElementById('clockH1').textContent = h[0];
  document.getElementById('clockH2').textContent = h[1];
  document.getElementById('clockM1').textContent = m[0];
  document.getElementById('clockM2').textContent = m[1];
  document.getElementById('clockS1').textContent = s[0];
  document.getElementById('clockS2').textContent = s[1];
  document.getElementById('clockAmPm').textContent = rawHrs >= 12 ? 'PM' : 'AM';
}

document.addEventListener('DOMContentLoaded', function () {
  if (document.getElementById('clockH1')) {
    updateClock();
    setInterval(updateClock, 1000);
  }
});