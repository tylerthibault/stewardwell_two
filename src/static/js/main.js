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

/* ── Custom tab system ─────────────────────────────────────────────────────
   Handles [data-my-toggle="tab"] buttons with [data-my-target="#pane-id"].
   Adds/removes the `active` class on both the button and its target pane.
─────────────────────────────────────────────────────────────────────────── */
(function () {
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-my-toggle="tab"]');
    if (!btn) return;

    var targetSelector = btn.getAttribute('data-my-target');
    if (!targetSelector) return;

    var targetPane = document.querySelector(targetSelector);
    if (!targetPane) return;

    // Deactivate all sibling tab buttons in the same list
    var tabList = btn.closest('[role="tablist"]');
    if (tabList) {
      tabList.querySelectorAll('[data-my-toggle="tab"]').forEach(function (b) {
        b.classList.remove('active');
      });
    }

    // Deactivate all sibling panes (look inside the nearest .my-tab-content)
    var tabContent = targetPane.closest('.my-tab-content');
    if (tabContent) {
      tabContent.querySelectorAll('.my-tab-pane').forEach(function (p) {
        p.classList.remove('active');
      });
    }

    btn.classList.add('active');
    targetPane.classList.add('active');
  });
}());
