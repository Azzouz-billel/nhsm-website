// Pomodoro focus timer. Runs for everyone; logs completed focus blocks to the
// account only when signed in and a module is selected.
(function () {
  "use strict";

  var root = document.querySelector("[data-timer]");
  if (!root) return;

  var els = {
    phase: root.querySelector("[data-phase]"),
    time: root.querySelector("[data-time]"),
    ring: root.querySelector("[data-ring]"),
    dots: root.querySelectorAll("[data-dots] .dot"),
    start: root.querySelector("[data-start]"),
    skip: root.querySelector("[data-skip]"),
    reset: root.querySelector("[data-reset]"),
    submit: root.querySelector("[data-submit]"),
    subject: root.querySelector("[data-subject]"),
    focus: root.querySelector("[data-focus]"),
    brk: root.querySelector("[data-break]"),
    hint: root.querySelector("[data-hint]"),
  };

  var LONG_BREAK_MIN = 15;
  var CYCLES = 4;
  var RADIUS = 120;
  var CIRC = 2 * Math.PI * RADIUS;
  els.ring.style.strokeDasharray = CIRC;

  var PHASE_LABEL = { focus: "Focus", break: "Short break", long: "Long break" };

  var auth = root.getAttribute("data-auth") === "1";
  var STORE_KEY = "nhsm-timer";
  // Resuming a block that ended longer ago than this (e.g. a tab left open
  // overnight) is treated as stale rather than logging a phantom focus block.
  var STALE_MS = 60 * 60 * 1000;
  var state = {
    phase: "focus",
    total: 25 * 60,
    remaining: 25 * 60,
    running: false,
    completedFocus: 0,
    endAt: null,
  };
  var ticker = null;
  var audioCtx = null;

  function focusSeconds() {
    return clampInt(els.focus.value, 1, 60, 25) * 60;
  }
  function breakSeconds() {
    return clampInt(els.brk.value, 1, 30, 5) * 60;
  }
  function clampInt(value, min, max, fallback) {
    var n = parseInt(value, 10);
    if (isNaN(n)) return fallback;
    return Math.min(max, Math.max(min, n));
  }

  function phaseSeconds(phase) {
    if (phase === "focus") return focusSeconds();
    if (phase === "long") return LONG_BREAK_MIN * 60;
    return breakSeconds();
  }

  function fmt(totalSeconds) {
    var m = Math.floor(totalSeconds / 60);
    var s = totalSeconds % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  function render() {
    els.time.textContent = fmt(state.remaining);
    els.phase.textContent = PHASE_LABEL[state.phase];
    root.setAttribute("data-current-phase", state.phase);
    var progress = state.total ? state.remaining / state.total : 0;
    els.ring.style.strokeDashoffset = CIRC * (1 - progress);
    els.start.textContent = state.running ? "Pause" : "Start";
    document.title = fmt(state.remaining) + " · " + PHASE_LABEL[state.phase] + " — NHSM Hub";
    renderDots();
  }

  function renderDots() {
    var filled = state.phase === "long" ? CYCLES : state.completedFocus % CYCLES;
    els.dots.forEach(function (dot, i) {
      dot.classList.toggle("dot--on", i < filled);
    });
  }

  function setPhase(phase) {
    state.phase = phase;
    state.total = phaseSeconds(phase);
    state.remaining = state.total;
    if (state.running) state.endAt = Date.now() + state.total * 1000;
    render();
    persist();
  }

  function tick() {
    state.remaining = Math.round((state.endAt - Date.now()) / 1000);
    if (state.remaining <= 0) {
      state.remaining = 0;
      completePhase();
    } else {
      render();
    }
  }

  function completePhase() {
    beep();
    if (state.phase === "focus") {
      var minutes = Math.round(state.total / 60);
      state.completedFocus += 1;
      logBlock(minutes);
      var next = state.completedFocus % CYCLES === 0 ? "long" : "break";
      setPhase(next);
    } else {
      setPhase("focus");
    }
    // Keep auto-running into the next phase.
    render();
  }

  function start() {
    if (state.running) return;
    if (auth && state.phase === "focus" && !els.subject.value) {
      els.hint.textContent = "Pick a module so your time gets logged.";
      return;
    }
    els.hint.textContent = "";
    ensureAudio();
    state.running = true;
    state.endAt = Date.now() + state.remaining * 1000;
    ticker = setInterval(tick, 1000);
    render();
    persist();
  }

  function pause() {
    if (state.running && state.endAt) {
      state.remaining = Math.max(0, Math.round((state.endAt - Date.now()) / 1000));
    }
    state.running = false;
    state.endAt = null;
    clearInterval(ticker);
    render();
    persist();
  }

  function toggle() {
    state.running ? pause() : start();
  }

  function skip() {
    pause();
    setPhase(state.phase === "focus" ? "break" : "focus");
  }

  function reset() {
    pause();
    state.completedFocus = 0;
    setPhase("focus");
  }

  // Log the focus minutes elapsed so far without finishing the block, then
  // restart the block so the same minutes aren't counted again on completion.
  function submitPartial() {
    if (!auth) {
      els.hint.textContent = "Sign in to save your study time.";
      return;
    }
    if (!els.subject.value) {
      els.hint.textContent = "Pick a module so your time gets logged.";
      return;
    }
    if (state.phase !== "focus") {
      els.hint.textContent = "Only focus time is saved — switch to a focus block.";
      return;
    }
    var minutes = Math.round((state.total - state.remaining) / 60);
    if (minutes < 1) {
      els.hint.textContent = "Study at least a minute before saving.";
      return;
    }
    logBlock(minutes);
    els.hint.textContent = "Saved " + minutes + " min ✓";
    pause();
    setPhase("focus");
  }

  function logBlock(minutes) {
    if (!auth || !els.subject.value) return;
    var meta = document.querySelector('meta[name="csrf-token"]');
    fetch(root.getAttribute("data-session-url"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": meta ? meta.content : "",
      },
      body: JSON.stringify({ subject: els.subject.value, minutes: minutes }),
    })
      .then(function (res) {
        return res.ok ? res.json() : Promise.reject();
      })
      .then(updateStats)
      .catch(function () {
        els.hint.textContent = "Couldn't save that block — check your connection.";
      });
  }

  function updateStats(data) {
    setStat("[data-stat-today]", data.today_minutes);
    setStat("[data-stat-streak]", data.current_streak);
    setStat("[data-stat-total]", data.total_study_minutes);
    setStat("[data-stat-sessions]", data.total_sessions);
  }
  function setStat(selector, value) {
    var el = document.querySelector(selector);
    if (el && value != null) el.textContent = value;
  }

  function ensureAudio() {
    if (audioCtx) return;
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
      audioCtx = null;
    }
  }
  function beep() {
    if (!audioCtx) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.frequency.value = 660;
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.4);
    } catch (e) {
      /* audio unavailable — silent */
    }
  }

  function persist() {
    try {
      localStorage.setItem(
        STORE_KEY,
        JSON.stringify({
          phase: state.phase,
          completedFocus: state.completedFocus,
          running: state.running,
          endAt: state.endAt,
          remaining: state.remaining,
          focus: els.focus.value,
          brk: els.brk.value,
          subject: els.subject.value,
        })
      );
    } catch (e) {
      /* storage unavailable — the timer still works for this page view */
    }
  }

  // Restore a timer saved on a previous page view so it keeps running across
  // navigations. The countdown is wall-clock based (endAt), so time elapsed
  // while away is accounted for instead of lost.
  function restore() {
    var raw;
    try {
      raw = localStorage.getItem(STORE_KEY);
    } catch (e) {
      return;
    }
    if (!raw) return;
    var saved;
    try {
      saved = JSON.parse(raw);
    } catch (e) {
      return;
    }

    if (saved.focus != null) els.focus.value = saved.focus;
    if (saved.brk != null) els.brk.value = saved.brk;
    if (saved.subject != null) els.subject.value = saved.subject;

    state.phase = saved.phase || "focus";
    state.completedFocus = saved.completedFocus || 0;
    state.total = phaseSeconds(state.phase);

    if (saved.running && saved.endAt) {
      state.endAt = saved.endAt;
      state.running = true;
      state.remaining = Math.round((state.endAt - Date.now()) / 1000);
      if (state.remaining <= 0) {
        // The phase finished while we were away. Ignore a long-abandoned timer;
        // otherwise complete that block and roll into the next phase.
        if (Date.now() - state.endAt > STALE_MS) {
          state.running = false;
          state.endAt = null;
          state.completedFocus = 0;
          setPhase("focus");
          return;
        }
        completePhase();
      }
      ticker = setInterval(tick, 1000);
    } else {
      state.running = false;
      state.endAt = null;
      state.remaining = saved.remaining != null ? saved.remaining : state.total;
    }
  }

  els.start.addEventListener("click", toggle);
  els.skip.addEventListener("click", skip);
  els.reset.addEventListener("click", reset);
  if (els.submit) els.submit.addEventListener("click", submitPartial);
  els.subject.addEventListener("change", persist);

  // Editing durations re-arms the current phase when paused, and is saved
  // either way so the change survives a page navigation.
  [els.focus, els.brk].forEach(function (input) {
    input.addEventListener("change", function () {
      if (!state.running) setPhase(state.phase);
      else persist();
    });
  });

  restore();
  render();
})();
