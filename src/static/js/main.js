/* ── Flash message auto-dismiss with progress bar ─────────────────────────
   Each .flash has a .flash-progress child whose scaleX shrinks from 1 → 0
   over DURATION ms. Hovering pauses the countdown; leaving resumes it.
─────────────────────────────────────────────────────────────────────────── */
(function () {
  const DURATION = 4000; // ms before a flash auto-dismisses

  document.querySelectorAll('.flash').forEach(function (flash) {
    var progress = flash.querySelector('.flash-progress');
    if (!progress) return;

    var remaining = DURATION;
    var lastTimestamp = null;
    var rafId = null;
    var paused = false;

    function step(timestamp) {
      if (lastTimestamp !== null) {
        remaining -= timestamp - lastTimestamp;
      }
      lastTimestamp = timestamp;

      var scale = Math.max(0, remaining / DURATION);
      progress.style.transform = 'scaleX(' + scale + ')';

      if (remaining <= 0) {
        dismiss();
        return;
      }

      if (!paused) {
        rafId = requestAnimationFrame(step);
      }
    }

    function dismiss() {
      flash.classList.add('flash-dismissing');
      setTimeout(function () {
        if (flash.parentNode) flash.parentNode.removeChild(flash);
      }, 300);
    }

    flash.addEventListener('mouseenter', function () {
      paused = true;
      cancelAnimationFrame(rafId);
      lastTimestamp = null;
    });

    flash.addEventListener('mouseleave', function () {
      paused = false;
      lastTimestamp = null;
      rafId = requestAnimationFrame(step);
    });

    // Kick off the timer
    rafId = requestAnimationFrame(step);
  });
}());
