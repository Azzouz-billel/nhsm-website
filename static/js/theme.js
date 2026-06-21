// Dark-mode toggle. The initial theme is set by the inline script in <head>
// (saved preference, else OS preference); this only handles the click + persists.
// Per-account persistence for signed-in users arrives in Phase 2.
(function () {
  "use strict";

  var KEY = "nhsm-theme";
  var root = document.documentElement;
  var btn = document.querySelector("[data-theme-toggle]");
  if (!btn) return;

  function currentTheme() {
    return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    btn.setAttribute("aria-pressed", String(theme === "dark"));
    btn.setAttribute(
      "aria-label",
      theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
    );
  }

  // For signed-in users, persist the choice to their account so it follows
  // them across devices (and overrides localStorage on next load).
  function persistForUser(theme) {
    if (btn.getAttribute("data-auth") !== "1") return;
    var meta = document.querySelector('meta[name="csrf-token"]');
    fetch(btn.getAttribute("data-theme-url"), {
      method: "POST",
      headers: {
        "X-CSRFToken": meta ? meta.content : "",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "theme=" + theme,
    }).catch(function () {
      /* offline / server error — localStorage still holds the choice */
    });
  }

  apply(currentTheme()); // sync the button with the pre-paint theme

  btn.addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(KEY, next);
    } catch (e) {
      /* storage may be unavailable; the toggle still works for this page */
    }
    apply(next);
    persistForUser(next);
  });
})();
