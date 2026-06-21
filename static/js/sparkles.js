// Hero sparkles via tsParticles (loaded from the slim CDN bundle). This is the
// vanilla-JS equivalent of the React `sparkles.tsx` component — same engine,
// brand-violet particles, themed from the CSS design tokens.
(function () {
  "use strict";

  var mount = document.getElementById("sparkles-hero");
  if (!mount || typeof tsParticles === "undefined") return;

  // Respect users who prefer no motion — leave the hero static.
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var brand =
    getComputedStyle(document.documentElement).getPropertyValue("--brand").trim() ||
    "#5a4ff3";

  tsParticles.load({
    id: "sparkles-hero",
    options: {
      fullScreen: { enable: false },
      fpsLimit: 60,
      detectRetina: true,
      background: { color: { value: "transparent" } },
      particles: {
        number: { value: 120, density: { enable: true, width: 800, height: 800 } },
        color: { value: brand },
        shape: { type: "circle" },
        size: { value: { min: 0.5, max: 1.9 } },
        opacity: {
          value: { min: 0.1, max: 0.85 },
          animation: { enable: true, speed: 1.4, sync: false, startValue: "random" },
        },
        move: {
          enable: true,
          direction: "none",
          speed: { min: 0.05, max: 0.45 },
          straight: false,
          outModes: { default: "out" },
        },
      },
      // Decorative only — no hover/click interactivity.
      interactivity: {
        events: {
          onHover: { enable: false },
          onClick: { enable: false },
          resize: { enable: true },
        },
      },
    },
  });
})();
