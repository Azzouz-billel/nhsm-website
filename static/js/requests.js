// Request board: toggle upvotes without a full page reload.
(function () {
  "use strict";

  var meta = document.querySelector('meta[name="csrf-token"]');

  document.querySelectorAll("[data-vote]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var btn = form.querySelector("[data-vote-btn]");
      fetch(form.action, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": meta ? meta.content : "",
        },
      })
        .then(function (res) {
          if (res.redirected) {
            window.location = res.url; // not logged in → login page
            return null;
          }
          if (!res.ok) throw new Error("Vote failed");
          return res.json();
        })
        .then(function (data) {
          if (!data) return;
          btn.querySelector("[data-vote-count]").textContent = data.count;
          btn.classList.toggle("voted", data.voted);
          btn.setAttribute("aria-pressed", String(data.voted));
        })
        .catch(function () {
          form.submit(); // fall back to a normal POST
        });
    });
  });
})();
