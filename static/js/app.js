// Site-wide behavior: mobile nav + scroll reveal animations.
(function () {
  "use strict";

  // Mobile nav toggle.
  var toggle = document.querySelector("[data-nav-toggle]");
  var links = document.querySelector("[data-nav-links]");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // Scroll reveals. CSS hides .reveal only when JS is present, so content
  // stays visible if this script (or GSAP) fails to load.
  function initReveals() {
    var els = document.querySelectorAll(".reveal");
    if (!window.gsap) {
      els.forEach(function (el) { el.style.opacity = 1; });
      return;
    }
    if (window.ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
    }
    els.forEach(function (el) {
      gsap.fromTo(
        el,
        { opacity: 0, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.7,
          ease: "power2.out",
          scrollTrigger: { trigger: el, start: "top 85%" },
        }
      );
    });
  }

  if (document.readyState !== "loading") {
    initReveals();
  } else {
    window.addEventListener("DOMContentLoaded", initReveals);
  }
})();
