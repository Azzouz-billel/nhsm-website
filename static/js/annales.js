// Annales archive: read filters, query the exam search API, render exam cards.
(function () {
  "use strict";

  var grid = document.querySelector("[data-results]");
  var countEl = document.querySelector("[data-results-count]");
  var emptyEl = document.querySelector("[data-empty]");
  if (!grid) return;

  var state = { q: "", year: "", semester: "", speciality: "", subject: "", type: "", solution: "" };
  var debounceTimer = null;

  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = value == null ? "" : value;
    return div.innerHTML;
  }

  function solutionMarkup(exam) {
    if (!exam.has_solution) return "";
    if (exam.solution_link) {
      return (
        '<a class="btn btn-ghost btn-sm" href="' + encodeURI(exam.solution_link) +
        '" target="_blank" rel="noopener">Corrigé →</a>'
      );
    }
    return '<span class="badge badge-solution">Corrigé available</span>';
  }

  function cardHtml(exam) {
    return (
      '<article class="resource-card">' +
        '<div class="meta">' +
          '<span class="badge">' + escapeHtml(exam.type_label) + "</span>" +
          '<span class="badge sem">' + escapeHtml(exam.year) + "</span>" +
          '<span class="badge sem">S' + escapeHtml(exam.semester) + "</span>" +
          (exam.speciality ? '<span class="badge spec">' + escapeHtml(exam.speciality_label) + "</span>" : "") +
        "</div>" +
        "<h3>" + escapeHtml(exam.title) + "</h3>" +
        '<p class="subj">' + escapeHtml(exam.subject_name) + "</p>" +
        '<div class="open card-actions">' +
          '<a class="btn btn-primary btn-sm" href="' + encodeURI(exam.drive_link) +
            '" target="_blank" rel="noopener">Open paper →</a>' +
          solutionMarkup(exam) +
        "</div>" +
      "</article>"
    );
  }

  function render(results, total) {
    if (total == null) total = results.length;
    countEl.textContent = total + (total === 1 ? " paper" : " papers");
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
    fetch("/api/exams/search?" + params.toString(), {
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
        countEl.textContent = "Could not load exam papers.";
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

  document.querySelectorAll("[data-filter]").forEach(function (input) {
    var key = input.getAttribute("data-filter");
    var immediate = input.tagName === "SELECT";
    input.addEventListener(immediate ? "change" : "input", function () {
      state[key] = input.value;
      scheduleFetch(immediate);
    });
  });

  document.querySelectorAll("[data-filter-check]").forEach(function (check) {
    var key = check.getAttribute("data-filter-check");
    check.addEventListener("change", function () {
      state[key] = check.checked ? check.value : "";
      scheduleFetch(true);
    });
  });

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

  var reset = document.querySelector("[data-filter-reset]");
  if (reset) {
    reset.addEventListener("click", function () {
      state = { q: "", year: "", semester: "", speciality: "", subject: "", type: "", solution: "" };
      document.querySelectorAll("[data-filter]").forEach(function (i) { i.value = ""; });
      document.querySelectorAll("[data-filter-check]").forEach(function (c) { c.checked = false; });
      document.querySelectorAll("[data-filter-chip]").forEach(function (c) {
        c.setAttribute("aria-pressed", c.getAttribute("data-value") === "" ? "true" : "false");
      });
      fetchResults();
    });
  }

  fetchResults();
})();
