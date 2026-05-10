/**
 * timer.js — Live session timer for Stewardwell Timed Turn Taker
 *
 * Exports a single function: startLiveTimer(startedAt, coinsPerMinute, timeLimitMinutes)
 *   startedAt        — JS Date object (UTC)
 *   coinsPerMinute   — integer cost rate
 *   timeLimitMinutes — integer; soft warning fires once at this threshold
 */

function startLiveTimer(startedAt, coinsPerMinute, timeLimitMinutes) {
    var timerDisplay = document.getElementById('timer-display');
    var liveCostEl   = document.getElementById('live-cost');
    var warnFired    = false;

    function pad(n) {
        return n < 10 ? '0' + n : String(n);
    }

    function tick() {
        var now     = new Date();
        var elapsed = Math.floor((now - startedAt) / 1000); // total seconds

        var h = Math.floor(elapsed / 3600);
        var m = Math.floor((elapsed % 3600) / 60);
        var s = elapsed % 60;

        if (timerDisplay) {
            timerDisplay.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
        }

        // Live coin cost — ceil(elapsed_seconds / 60) × rate, minimum 0
        var minutesElapsed = elapsed > 0 ? Math.ceil(elapsed / 60) : 0;
        var liveCost = minutesElapsed * coinsPerMinute;
        if (liveCostEl) {
            liveCostEl.textContent = liveCost;
        }

        // Soft warning at time limit
        if (!warnFired && timeLimitMinutes > 0 && elapsed >= timeLimitMinutes * 60) {
            warnFired = true;
            if (typeof showMessage === 'function') {
                showMessage(
                    '⏰ ' + timeLimitMinutes + ' minutes reached! You can keep playing, but your turn is up.',
                    'info'
                );
            }
        }
    }

    // Run immediately then every second
    tick();
    setInterval(tick, 1000);
}
