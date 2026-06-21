// Resource library: read the filter controls, query the search API, render cards.
(function () {
  "use strict";

  var grid = document.querySelector("[data-results]");
  var countEl = document.querySelector("[data-results-count]");
  var emptyEl = document.querySelector("[data-empty]");
  if (!grid) return;

  var state = { q: "", semester: "", subject: "", type: "" };
  var debounceTimer = null;

  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = value == null ? "" : value;
    return div.innerHTML;
  }

  function cardHtml(r) {
    return (
      '<article class="resource-card">' +
        '<div class="meta">' +
          '<span class="badge">' + escapeHtml(r.type_label) + "</span>" +
          '<span class="badge sem">S' + escapeHtml(r.semester) + "</span>" +
        "</div>" +
        "<h3>" + escapeHtml(r.title) + "</h3>" +
        '<p class="subj">' + escapeHtml(r.subject_name) + "</p>" +
        '<div class="open">' +
          '<a class="btn btn-primary btn-sm" href="' + encodeURI(r.drive_link) +
            '" target="_blank" rel="noopener">Open in Drive →</a>' +
        "</div>" +
      "</article>"
    );
  }

  function render(results, total) {
    if (total == null) total = results.length;
    countEl.textContent = total + (total === 1 ? " resource" : " resources");
    if (!results.length) {
      grid.innerHTML = "";
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    grid.innerHTML = results.map(cardHtml).join("");
  }

  function fetchResults() {
    var params = new URLSearchParams();
    Object.keys(state).forEach(function (key) {
      if (state[key]) params.set(key, state[key]);
    });
    fetch("/api/resources/search?" + params.toString(), {
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Search failed");
        return res.json();
      })
      .then(function (data) {
        var results = data.results || data;
        render(results, data.count);
      })
      .catch(function () {
        countEl.textContent = "Could not load resources.";
      });
  }

  function scheduleFetch(immediate) {
    clearTimeout(debounceTimer);
    if (immediate) {
      fetchResults();
    } else {
      debounceTimer = setTimeout(fetchResults, 250);
    }
  }

  // Select / search inputs.
  document.querySelectorAll("[data-filter]").forEach(function (input) {
    var key = input.getAttribute("data-filter");
    var immediate = input.tagName === "SELECT";
    input.addEventListener(immediate ? "change" : "input", function () {
      state[key] = input.value;
      scheduleFetch(immediate);
    });
  });

  // Type chips (single-select).
  document.querySelectorAll("[data-filter-chip]").forEach(function (chip) {
    chip.addEventListener("click", function () {
      var group = chip.getAttribute("data-filter-chip");
      document
        .querySelectorAll('[data-filter-chip="' + group + '"]')
        .forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      chip.setAttribute("aria-pressed", "true");
      state[group] = chip.getAttribute("data-value");
      scheduleFetch(true);
    });
  });

  // Clear filters.
  var reset = document.querySelector("[data-filter-reset]");
  if (reset) {
    reset.addEventListener("click", function () {
      state = { q: "", semester: "", subject: "", type: "" };
      document.querySelectorAll("[data-filter]").forEach(function (i) { i.value = ""; });
      document.querySelectorAll("[data-filter-chip]").forEach(function (c) {
        c.setAttribute("aria-pressed", c.getAttribute("data-value") === "" ? "true" : "false");
      });
      fetchResults();
    });
  }

  fetchResults();
})();
