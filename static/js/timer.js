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
    custom: root.querySelector("[data-custom]"),
    focusMode: root.querySelector("[data-focus-mode]"),
    focusExit: root.querySelector("[data-focus-exit]"),
    ambientToggle: root.querySelector("[data-ambient-toggle]"),
    ambientLabel: root.querySelector("[data-ambient-label]"),
    focus: root.querySelector("[data-focus]"),
    brk: root.querySelector("[data-break]"),
    hint: root.querySelector("[data-hint]"),
  };

  var LONG_BREAK_MIN = 15;
  var CYCLES = 4;
  var RADIUS = 120;
  var CIRC = 2 * Math.PI * RADIUS;
  els.ring.style.strokeDasharray = CIRC;

  var PHASE_LABEL = { focus: "Focus Session", break: "Short Break", long: "Long Break" };

  var auth = root.getAttribute("data-auth") === "1";
  var STORE_KEY = "nhsm-timer";
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

  // Ambient Sound Synth (Web Audio API Rain)
  var ambientPlaying = false;
  var ambientSource = null;
  var ambientGain = null;

  function hasActivity() {
    return !!((els.subject && els.subject.value) || (els.custom && els.custom.value.trim()));
  }

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
    render();
  }

  function start() {
    if (state.running) return;
    if (auth && state.phase === "focus" && !hasActivity()) {
      els.hint.textContent = "Pick a module or write your own activity so your time gets logged.";
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

  function submitPartial() {
    if (state.phase !== "focus") {
      els.hint.textContent = "You're on a break already.";
      return;
    }
    var minutes = Math.round((state.total - state.remaining) / 60);
    var saved = minutes >= 1 && hasActivity();
    if (saved) {
      logBlock(minutes);
      state.completedFocus += 1;
      els.hint.textContent = "Saved " + minutes + " min ✓ — break time.";
    } else if (!hasActivity()) {
      els.hint.textContent = "Pick a module or write an activity to log your time — taking a break.";
    } else {
      els.hint.textContent = "Studied under a minute — taking a break.";
    }
    pause();
    var longBreak = saved && state.completedFocus % CYCLES === 0;
    setPhase(longBreak ? "long" : "break");
  }

  function logBlock(minutes) {
    if (!auth || !hasActivity()) return;
    var meta = document.querySelector('meta[name="csrf-token"]');
    var payload = { minutes: minutes };
    if (els.subject.value) payload.subject = els.subject.value;
    else payload.label = els.custom.value.trim();
    fetch(root.getAttribute("data-session-url"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": meta ? meta.content : "",
      },
      body: JSON.stringify(payload),
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

  // Ambient Rain Audio Synthesis
  function toggleAmbientSound() {
    ensureAudio();
    if (!audioCtx) return;
    if (ambientPlaying) {
      stopAmbientSound();
    } else {
      startAmbientSound();
    }
  }

  function startAmbientSound() {
    if (!audioCtx) return;
    if (audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    var bufferSize = 2 * audioCtx.sampleRate;
    var noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    var output = noiseBuffer.getChannelData(0);
    var b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
    for (var i = 0; i < bufferSize; i++) {
      var white = Math.random() * 2 - 1;
      b0 = 0.99886 * b0 + white * 0.0555179;
      b1 = 0.99332 * b1 + white * 0.0750759;
      b2 = 0.96900 * b2 + white * 0.1538520;
      b3 = 0.86650 * b3 + white * 0.3104856;
      b4 = 0.55000 * b4 + white * 0.5329522;
      b5 = -0.7616 * b5 - white * 0.0168980;
      output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
      output[i] *= 0.05;
      b6 = white * 0.115926;
    }
    ambientSource = audioCtx.createBufferSource();
    ambientSource.buffer = noiseBuffer;
    ambientSource.loop = true;

    var filter = audioCtx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 1000;

    ambientGain = audioCtx.createGain();
    ambientGain.gain.setValueAtTime(0.01, audioCtx.currentTime);
    ambientGain.gain.exponentialRampToValueAtTime(0.18, audioCtx.currentTime + 0.8);

    ambientSource.connect(filter);
    filter.connect(ambientGain);
    ambientGain.connect(audioCtx.destination);

    ambientSource.start();
    ambientPlaying = true;
    updateAmbientUI();
  }

  function stopAmbientSound() {
    if (ambientGain && audioCtx) {
      ambientGain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
      setTimeout(function() {
        if (ambientSource) {
          try { ambientSource.stop(); } catch(e){}
          ambientSource = null;
        }
      }, 400);
    }
    ambientPlaying = false;
    updateAmbientUI();
  }

  function updateAmbientUI() {
    if (els.ambientToggle && els.ambientLabel) {
      if (ambientPlaying) {
        els.ambientToggle.classList.add("btn-ambient-active");
        els.ambientLabel.textContent = "Ambient Rain: Playing 🌧️";
      } else {
        els.ambientToggle.classList.remove("btn-ambient-active");
        els.ambientLabel.textContent = "Ambient Rain: Off";
      }
    }
  }

  if (els.ambientToggle) {
    els.ambientToggle.addEventListener("click", toggleAmbientSound);
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
          custom: els.custom.value,
        })
      );
    } catch (e) {
      /* storage unavailable */
    }
  }

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
    if (saved.custom != null) els.custom.value = saved.custom;

    state.phase = saved.phase || "focus";
    state.completedFocus = saved.completedFocus || 0;
    state.total = phaseSeconds(state.phase);

    if (saved.running && saved.endAt) {
      state.endAt = saved.endAt;
      state.running = true;
      state.remaining = Math.round((state.endAt - Date.now()) / 1000);
      if (state.remaining <= 0) {
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

  // Full Screen Focus Mode
  function enterFocusMode() {
    document.body.classList.add("focus-mode");
    try {
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(function () {});
      }
    } catch (e) {
      /* fallback to CSS overlay */
    }
  }
  function exitFocusMode() {
    document.body.classList.remove("focus-mode");
    try {
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(function () {});
      }
    } catch (e) {
      /* not fullscreen */
    }
  }
  if (els.focusMode) els.focusMode.addEventListener("click", enterFocusMode);
  if (els.focusExit) els.focusExit.addEventListener("click", exitFocusMode);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && document.body.classList.contains("focus-mode")) {
      exitFocusMode();
    }
  });
  document.addEventListener("fullscreenchange", function () {
    if (!document.fullscreenElement) {
      document.body.classList.remove("focus-mode");
    }
  });

  els.subject.addEventListener("change", function () {
    if (els.subject.value) els.custom.value = "";
    persist();
  });
  els.custom.addEventListener("input", function () {
    if (els.custom.value.trim()) els.subject.value = "";
    persist();
  });

  [els.focus, els.brk].forEach(function (input) {
    input.addEventListener("change", function () {
      if (!state.running) setPhase(state.phase);
      else persist();
    });
  });

  // Box Breathing Widget
  var breathBtn = document.querySelector("[data-breath-start]");
  var breathCircle = document.querySelector("[data-breath-circle]");
  var breathText = document.querySelector("[data-breath-text]");
  var breathInterval = null;

  if (breathBtn && breathCircle && breathText) {
    var phases = [
      { text: "Inhale...", scale: "1.3", class: "inhale" },
      { text: "Hold...", scale: "1.3", class: "hold" },
      { text: "Exhale...", scale: "0.85", class: "exhale" },
      { text: "Hold...", scale: "0.85", class: "hold" },
    ];
    var breathIdx = 0;
    var breathRunning = false;

    breathBtn.addEventListener("click", function() {
      if (breathRunning) {
        clearInterval(breathInterval);
        breathRunning = false;
        breathText.textContent = "Click Start";
        breathBtn.textContent = "Start 2-Min Reset";
        breathCircle.style.transform = "scale(1)";
        return;
      }
      breathRunning = true;
      breathBtn.textContent = "Stop Exercise";
      runBreathCycle();
      breathInterval = setInterval(runBreathCycle, 4000);
    });

    function runBreathCycle() {
      var p = phases[breathIdx % phases.length];
      breathText.textContent = p.text;
      breathCircle.style.transform = "scale(" + p.scale + ")";
      breathIdx++;
    }
  }

  // 1-Minute Stretch Prompt Generator
  var stretches = [
    { title: "20-20-20 Eye Rest", desc: "Look at an object 20 feet away for 20 seconds to relax your eye ciliary muscles." },
    { title: "Neck Rolls", desc: "Slowly roll your head in a circle 5 times clockwise, then 5 times counter-clockwise." },
    { title: "Shoulder Shrugs", desc: "Raise your shoulders to your ears, hold for 3 seconds, and release 5 times." },
    { title: "Seated Spinal Twist", desc: "Sit tall, place your right hand on your left knee, and gently twist left for 15s." },
    { title: "Wrist & Finger Flex", desc: "Extend arms forward, pull fingers back gently with opposite hand for 15s per side." }
  ];
  var stretchIdx = 0;
  var stretchNextBtn = document.querySelector("[data-stretch-next]");
  var stretchTitle = document.querySelector("[data-stretch-title]");
  var stretchDesc = document.querySelector("[data-stretch-desc]");

  if (stretchNextBtn && stretchTitle && stretchDesc) {
    stretchNextBtn.addEventListener("click", function() {
      stretchIdx = (stretchIdx + 1) % stretches.length;
      stretchTitle.textContent = stretches[stretchIdx].title;
      stretchDesc.textContent = stretches[stretchIdx].desc;
    });
  }

  // NHSM Grade Simulator
  var gpaEmd = document.querySelector("[data-gpa-emd]");
  var gpaTd = document.querySelector("[data-gpa-td]");
  var gpaTp = document.querySelector("[data-gpa-tp]");
  var gpaRes = document.querySelector("[data-gpa-result]");

  function calcGpa() {
    if (!gpaRes) return;
    var emd = parseFloat(gpaEmd ? gpaEmd.value : "") || 0;
    var td = parseFloat(gpaTd ? gpaTd.value : "") || 0;
    var tp = parseFloat(gpaTp ? gpaTp.value : "") || 0;

    var hasTp = gpaTp && gpaTp.value.trim() !== "";
    var finalScore = 0;
    if (hasTp) {
      finalScore = (emd * 0.50) + (td * 0.25) + (tp * 0.25);
    } else {
      finalScore = (emd * 0.60) + (td * 0.40);
    }
    if (!gpaEmd.value && !gpaTd.value && !gpaTp.value) {
      gpaRes.innerHTML = 'Estimated Module Score: <strong>—</strong>';
    } else {
      var badge = finalScore >= 10 ? ' <span style="color:var(--success)">[PASS]</span>' : ' <span style="color:var(--danger)">[RATTRAPAGE]</span>';
      gpaRes.innerHTML = 'Estimated Module Score: <strong>' + finalScore.toFixed(2) + ' / 20</strong>' + badge;
    }
  }

  [gpaEmd, gpaTd, gpaTp].forEach(function(input) {
    if (input) input.addEventListener("input", calcGpa);
  });

  restore();
  render();
})();
