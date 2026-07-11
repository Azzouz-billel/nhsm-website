// Top news bar: rotate one message at a time, and let the user hide it.
// Each message slides in from its reading side (English L→R, Arabic R→L).
(function () {
  "use strict";

  var bar = document.querySelector("[data-news-bar]");
  if (!bar) return;

  var KEY = "nhsm-news-hidden";
  var sig = bar.getAttribute("data-news-sig") || "";

  // Already dismissed this exact set of news (the inline script may have hidden
  // it already) — leave it hidden and do nothing.
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

  var msgs = bar.querySelectorAll(".news-msg");
  if (!msgs.length) return;

  var index = 0;
  msgs[0].classList.add("is-active");
  if (msgs.length > 1) {
    window.setInterval(function () {
      msgs[index].classList.remove("is-active");
      index = (index + 1) % msgs.length;
      msgs[index].classList.add("is-active");
    }, 5000);
  }
})();
