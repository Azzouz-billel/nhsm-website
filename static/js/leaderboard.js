// Leaderboard: read filters, fetch rankings, render the table + MVP + my position.
(function () {
  "use strict";

  var root = document.querySelector("[data-lb]");
  if (!root) return;

  var api = root.getAttribute("data-api");
  var windowSel = root.querySelector("[data-filter-window]");
  var groupSel = root.querySelector("[data-filter-group]");
  var tbody = document.querySelector("[data-rows]");
  var emptyEl = document.querySelector("[data-empty]");
  var mvpEl = document.querySelector("[data-mvp]");
  var meEl = document.querySelector("[data-me]");
  var headers = document.querySelectorAll(".lb-table th.sortable");

  var sort = "minutes";

  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = value == null ? "" : value;
    return div.innerHTML;
  }

  function rowHtml(r) {
    return (
      '<tr class="' + (r.is_me ? "is-me" : "") + '">' +
        '<td class="col-rank">' + r.rank + "</td>" +
        "<td>" + escapeHtml(r.name) + "</td>" +
        '<td class="col-group muted">' + escapeHtml(r.group) + "</td>" +
        '<td class="col-num">' + r.minutes + "</td>" +
        '<td class="col-num">' + r.streak + "</td>" +
      "</tr>"
    );
  }

  function renderMvp(rows) {
    if (!rows.length) {
      mvpEl.hidden = true;
      return;
    }
    var top = rows[0];
    mvpEl.querySelector("[data-mvp-name]").textContent = top.name;
    mvpEl.querySelector("[data-mvp-meta]").textContent =
      top.minutes + " min · " + top.streak + "-day streak";
    mvpEl.hidden = false;
  }

  function renderMe(me) {
    if (!me) {
      meEl.hidden = true;
      return;
    }
    meEl.querySelector("[data-me-rank]").textContent = "#" + me.rank;
    meEl.querySelector("[data-me-meta]").textContent =
      me.minutes + " min · " + me.streak + "-day streak";
    meEl.hidden = false;
  }

  function syncHeaders() {
    headers.forEach(function (th) {
      var active = th.getAttribute("data-sort") === sort;
      th.classList.toggle("sorted", active);
      th.setAttribute("aria-sort", active ? "descending" : "none");
    });
  }

  function load() {
    var params = new URLSearchParams({
      window: windowSel.value,
      group: groupSel.value,
      sort: sort,
    });
    fetch(api + "?" + params.toString(), { headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) throw new Error("Failed");
        return res.json();
      })
      .then(function (data) {
        var rows = data.rows || [];
        tbody.innerHTML = rows.map(rowHtml).join("");
        emptyEl.hidden = rows.length > 0;
        renderMvp(rows);
        renderMe(data.me);
        syncHeaders();
      })
      .catch(function () {
        tbody.innerHTML = "";
        emptyEl.hidden = false;
        emptyEl.textContent = "Couldn't load the leaderboard.";
      });
  }

  windowSel.addEventListener("change", load);
  groupSel.addEventListener("change", load);
  headers.forEach(function (th) {
    th.addEventListener("click", function () {
      sort = th.getAttribute("data-sort");
      load();
    });
  });

  load();
})();
