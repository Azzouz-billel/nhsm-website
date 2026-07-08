// Count-up for the home hero stats: each [data-countup] number ticks from 1 to
// its server-rendered total. Leaves the final value in place for tiny counts,
// no-JS, or reduced-motion users.
(function () {
  "use strict";

  var els = document.querySelectorAll("[data-countup]");
  if (!els.length) return;

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  els.forEach(function (el) {
    var target = parseInt((el.textContent || "").replace(/\D/g, ""), 10);
    if (isNaN(target) || target <= 1 || reduceMotion) return; // keep final value

    var DURATION = 1800; // ms — how long the count-up takes. Bigger = slower.
    var start = null;
    el.textContent = "1";

    function frame(now) {
      if (start === null) start = now;
      var p = Math.min((now - start) / DURATION, 1);
      var eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = String(Math.max(1, Math.round(1 + (target - 1) * eased)));
      if (p < 1) {
        requestAnimationFrame(frame);
      } else {
        el.textContent = String(target);
      }
    }

    requestAnimationFrame(frame);
  });
})();
