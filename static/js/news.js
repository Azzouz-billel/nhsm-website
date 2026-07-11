// Top news bar: scroll one message at a time across the bar, each in its own
// reading direction (English L→R, Arabic R→L), then move to the next. Also
// lets the user hide the bar (remembered until the news changes).
(function () {
  "use strict";

  var bar = document.querySelector("[data-news-bar]");
  if (!bar) return;

  var KEY = "nhsm-news-hidden";
  var sig = bar.getAttribute("data-news-sig") || "";

  try {
    if (localStorage.getItem(KEY) === sig) {
      bar.style.display = "none";
      return;
    }
  } catch (e) {}

  var closeBtn = bar.querySelector("[data-news-close]");
  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      try {
        localStorage.setItem(KEY, sig);
      } catch (e) {}
      bar.classList.add("news-bar--closing");
      window.setTimeout(function () {
        bar.style.display = "none";
      }, 250);
    });
  }

  var msgs = Array.prototype.slice.call(bar.querySelectorAll(".news-msg"));
  if (!msgs.length) return;

  var index = 0;
  var reduce =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Reduced motion: no scrolling — show one, swap every 5s.
  if (reduce) {
    msgs[0].classList.add("is-active");
    if (msgs.length > 1) {
      window.setInterval(function () {
        msgs[index].classList.remove("is-active");
        index = (index + 1) % msgs.length;
        msgs[index].classList.add("is-active");
      }, 5000);
    }
    return;
  }

  var stage = bar.querySelector(".news-bar__stage");
  var SPEED = 90; // px/second — the ticker's reading pace

  function play(i) {
    var msg = msgs[i];
    // offsetWidth is available even while the message is visibility:hidden.
    var distance = stage.offsetWidth + msg.offsetWidth;
    msg.style.animationDuration = Math.max(6, distance / SPEED) + "s";
    msg.classList.add("is-active");
  }

  msgs.forEach(function (msg) {
    msg.addEventListener("animationend", function () {
      msg.classList.remove("is-active");
      void msg.offsetWidth; // reflow so re-adding restarts the animation
      index = (index + 1) % msgs.length;
      play(index);
    });
  });

  play(0);
})();
