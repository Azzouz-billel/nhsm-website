// Professors page: instant client-side filter of the list by name.
(function () {
  "use strict";

  var input = document.querySelector("[data-prof-search]");
  var list = document.querySelector("[data-prof-list]");
  var empty = document.querySelector("[data-prof-empty]");
  if (!input || !list) return;

  var rows = Array.prototype.slice.call(list.querySelectorAll(".prof-row"));

  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var match = !q || (row.getAttribute("data-name") || "").indexOf(q) !== -1;
      row.hidden = !match;
      if (match) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
  });
})();
