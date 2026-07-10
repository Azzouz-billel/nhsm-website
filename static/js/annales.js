// Annales archive: read filters, query the exam search API, render exam cards.
// Paginated: a "Load more" button fetches subsequent pages and appends them.
(function () {
  "use strict";

  var grid = document.querySelector("[data-results]");
  var countEl = document.querySelector("[data-results-count]");
  var emptyEl = document.querySelector("[data-empty]");
  var loadMoreBtn = document.querySelector("[data-load-more]");
  if (!grid) return;

  var state = { q: "", year: "", semester: "", speciality: "", subject: "", type: "", solution: "" };
  var debounceTimer = null;
  var page = 1;
  var loading = false;

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

  function skeletonMarkup(n) {
    var out = "";
    for (var i = 0; i < n; i++) out += '<div class="skeleton-card" aria-hidden="true"></div>';
    return out;
  }

  function render(results, total, append) {
    if (total == null) total = results.length;
    countEl.textContent = total + (total === 1 ? " paper" : " papers");
    if (append) {
      grid.insertAdjacentHTML("beforeend", results.map(cardHtml).join(""));
      return;
    }
    if (!results.length) {
      grid.innerHTML = "";
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    grid.innerHTML = results.map(cardHtml).join("");
  }

  function setLoadMore(hasNext) {
    if (!loadMoreBtn) return;
    loadMoreBtn.hidden = !hasNext;
    loadMoreBtn.disabled = false;
    loadMoreBtn.textContent = "Load more";
  }

  function fetchPage(append) {
    if (loading) return;
    loading = true;
    if (append && loadMoreBtn) {
      loadMoreBtn.disabled = true;
      loadMoreBtn.textContent = "Loading…";
    } else {
      grid.setAttribute("aria-busy", "true");
      if (!grid.children.length) grid.innerHTML = skeletonMarkup(6);
    }

    var params = new URLSearchParams();
    Object.keys(state).forEach(function (key) {
      if (state[key]) params.set(key, state[key]);
    });
    if (page > 1) params.set("page", page);

    fetch("/api/exams/search?" + params.toString(), { headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) throw new Error("Search failed");
        return res.json();
      })
      .then(function (data) {
        render(data.results || data, data.count, append);
        setLoadMore(!!data.next);
        grid.removeAttribute("aria-busy");
        loading = false;
      })
      .catch(function () {
        countEl.textContent = "Could not load exam papers.";
        setLoadMore(false);
        grid.removeAttribute("aria-busy");
        loading = false;
      });
  }

  function runSearch() {
    page = 1;
    fetchPage(false);
  }

  function scheduleFetch(immediate) {
    clearTimeout(debounceTimer);
    if (immediate) {
      runSearch();
    } else {
      debounceTimer = setTimeout(runSearch, 250);
    }
  }

  // Show only the modules for the chosen semester, and reveal the speciality
  // filter only for S7–S10 (never S1–S6).
  function applySemesterScope(sem) {
    var subjectSelect = document.getElementById("filter-subject");
    if (subjectSelect) {
      Array.prototype.forEach.call(subjectSelect.options, function (opt) {
        if (!opt.dataset.semester) return; // keep the "All modules" option
        opt.hidden = sem !== "" && opt.dataset.semester !== sem;
      });
      var selected = subjectSelect.selectedOptions[0];
      if (selected && selected.hidden) {
        subjectSelect.value = "";
        state.subject = "";
      }
    }
    var specGroup = document.querySelector("[data-speciality-group]");
    var specSelect = document.getElementById("filter-speciality");
    var showSpec = sem !== "" && Number(sem) >= 7 && Number(sem) <= 10;
    if (specGroup) specGroup.hidden = !showSpec;
    if (!showSpec && specSelect) {
      specSelect.value = "";
      state.speciality = "";
    }
  }

  document.querySelectorAll("[data-filter]").forEach(function (input) {
    if (input.id === "filter-semester") return;
    var key = input.getAttribute("data-filter");
    var immediate = input.tagName === "SELECT";
    input.addEventListener(immediate ? "change" : "input", function () {
      state[key] = input.value;
      scheduleFetch(immediate);
    });
  });

  var semesterSelect = document.getElementById("filter-semester");
  if (semesterSelect) {
    semesterSelect.addEventListener("change", function () {
      state.semester = semesterSelect.value;
      applySemesterScope(semesterSelect.value);
      scheduleFetch(true);
    });
  }

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

  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", function () {
      page += 1;
      fetchPage(true);
    });
  }

  var reset = document.querySelector("[data-filter-reset]");
  if (reset) {
    reset.addEventListener("click", function () {
      state = { q: "", year: "", semester: "", speciality: "", subject: "", type: "", solution: "" };
      document.querySelectorAll("[data-filter]").forEach(function (i) { i.value = ""; });
      document.querySelectorAll("[data-filter-check]").forEach(function (c) { c.checked = false; });
      document.querySelectorAll("[data-filter-chip]").forEach(function (c) {
        c.setAttribute("aria-pressed", c.getAttribute("data-value") === "" ? "true" : "false");
      });
      applySemesterScope("");
      runSearch();
    });
  }

  applySemesterScope("");
  runSearch();
})();
