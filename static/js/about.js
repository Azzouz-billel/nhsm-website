// About page: cross-fade the campus photo slideshow every 4 seconds.
(function () {
  "use strict";

  var box = document.querySelector("[data-slideshow]");
  if (!box) return;

  var slides = box.querySelectorAll(".about-slide");
  if (slides.length < 2) return; // a single photo needs no rotation

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) return; // the first slide stays shown

  var index = 0;
  setInterval(function () {
    slides[index].classList.remove("is-active");
    index = (index + 1) % slides.length;
    slides[index].classList.add("is-active");
  }, 4000);
})();
