const STORAGE_KEY = "kgc-weekend-stopwatch-v1";
const CIRCUMFERENCE = 2 * Math.PI * 104;

const DEFAULT_ACTIVITIES = [
  { id: "english", name: "영어 공부", minutes: 20 },
  { id: "exercise", name: "운동", minutes: 30 },
  { id: "reading", name: "독서", minutes: 25 },
  { id: "chores", name: "정리", minutes: 20 },
  { id: "rest", name: "휴식", minutes: 15 },
  { id: "free", name: "자유 스톱워치", minutes: 0 },
];

const els = {
  today: document.getElementById("today-label"),
  mode: document.getElementById("mode-pill"),
  time: document.getElementById("clock-time"),
  title: document.getElementById("activity-title"),
  sub: document.getElementById("clock-sub"),
  ring: document.getElementById("ring-progress"),
  toggle: document.getElementById("btn-toggle"),
  reset: document.getElementById("btn-reset"),
  done: document.getElementById("btn-done"),
  list: document.getElementById("activity-list"),
  addBtn: document.getElementById("btn-add"),
  addForm: document.getElementById("add-form"),
  addName: document.getElementById("add-name"),
  addMinutes: document.getElementById("add-minutes"),
  addCancel: document.getElementById("btn-add-cancel"),
  weekendTotal: document.getElementById("weekend-total"),
  bars: document.getElementById("weekend-bars"),
  sessions: document.getElementById("session-list"),
  clear: document.getElementById("btn-clear"),
  toast: document.getElementById("toast"),
  stage: document.querySelector(".stage"),
};

const state = {
  activities: [],
  sessions: [],
  selectedId: "english",
  running: false,
  accumulatedMs: 0,
  anchorTs: 0,
  completed: false,
  raf: 0,
};

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (Array.isArray(data.activities) && data.activities.length) {
      state.activities = data.activities;
    }
    if (Array.isArray(data.sessions)) state.sessions = data.sessions;
  } catch {
    /* keep defaults */
  }
}

function save() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      activities: state.activities,
      sessions: state.sessions,
    })
  );
}

function selected() {
  return state.activities.find((item) => item.id === state.selectedId) || state.activities[0];
}

function isStopwatch(activity = selected()) {
  return Number(activity.minutes) === 0;
}

function durationMs(activity = selected()) {
  return Number(activity.minutes) * 60 * 1000;
}

function elapsedMs() {
  if (!state.running) return state.accumulatedMs;
  return state.accumulatedMs + (Date.now() - state.anchorTs);
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function formatClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${pad(minutes)}:${pad(seconds)}`;
}

function formatMinutes(ms) {
  const totalSec = Math.max(1, Math.round(ms / 1000));
  if (totalSec < 60) return `${totalSec}초`;
  const minutes = Math.floor(totalSec / 60);
  const seconds = totalSec % 60;
  return seconds ? `${minutes}분 ${seconds}초` : `${minutes}분`;
}

function weekendRange(now = new Date()) {
  const day = now.getDay();
  const saturday = new Date(now);
  const offset = day === 0 ? -1 : 6 - day;
  saturday.setDate(now.getDate() + offset);
  saturday.setHours(0, 0, 0, 0);
  const sunday = new Date(saturday);
  sunday.setDate(saturday.getDate() + 1);
  sunday.setHours(23, 59, 59, 999);
  return { saturday, sunday };
}

function inThisWeekend(iso) {
  const date = new Date(iso);
  const { saturday, sunday } = weekendRange();
  return date >= saturday && date <= sunday;
}

function weekendSessions() {
  return state.sessions
    .filter((session) => inThisWeekend(session.endedAt))
    .sort((a, b) => new Date(b.endedAt) - new Date(a.endedAt));
}

function renderToday() {
  const now = new Date();
  const weekday = now.toLocaleDateString("ko-KR", { weekday: "long" });
  const date = now.toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
  const weekend = now.getDay() === 0 || now.getDay() === 6;
  els.today.textContent = weekend ? `${date} ${weekday} · 주말` : `${date} ${weekday}`;
}

function renderActivities() {
  els.list.innerHTML = "";
  state.activities.forEach((activity) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `activity${activity.id === state.selectedId ? " active" : ""}`;
    const name = document.createElement("span");
    name.className = "activity-name";
    name.textContent = activity.name;
    const meta = document.createElement("span");
    meta.className = "activity-meta";
    meta.textContent = activity.minutes ? `${activity.minutes}분` : "스톱워치";
    btn.append(name, meta);
    btn.addEventListener("click", () => selectActivity(activity.id));
    li.appendChild(btn);
    els.list.appendChild(li);
  });
}

function renderClock() {
  const activity = selected();
  const elapsed = elapsedMs();
  const stopwatch = isStopwatch(activity);
  const remaining = Math.max(0, durationMs(activity) - elapsed);
  const display = stopwatch ? elapsed : remaining;
  const progress = stopwatch
    ? Math.min(elapsed / Math.max(elapsed, 20 * 60 * 1000), 1)
    : remaining / Math.max(durationMs(activity), 1);

  els.time.textContent = formatClock(display);
  els.title.textContent = activity.name;
  els.sub.textContent = stopwatch
    ? state.running
      ? "자유롭게 측정 중"
      : "목표 없이 측정"
    : `목표 ${activity.minutes}분`;
  els.mode.textContent = stopwatch ? "스톱워치" : "타이머";
  els.ring.style.strokeDasharray = String(CIRCUMFERENCE);
  els.ring.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - progress));
  els.stage.classList.toggle("running", state.running);
  els.stage.classList.toggle("done", state.completed);
  els.toggle.textContent = state.running ? "일시정지" : state.accumulatedMs ? "계속" : "시작";
  els.done.hidden = !stopwatch || elapsed < 1000 || state.running;
}

function renderSessions() {
  const sessions = weekendSessions();
  const totals = new Map();
  let totalMs = 0;
  sessions.forEach((session) => {
    totalMs += session.actualMs;
    totals.set(session.name, (totals.get(session.name) || 0) + session.actualMs);
  });

  els.weekendTotal.textContent = totalMs ? formatMinutes(totalMs) : "0분";
  els.bars.innerHTML = "";
  const max = Math.max(...totals.values(), 1);
  [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .forEach(([name, ms]) => {
      const row = document.createElement("div");
      row.className = "bar-row";
      const label = document.createElement("span");
      label.textContent = name;
      const track = document.createElement("div");
      track.className = "bar-track";
      const fill = document.createElement("div");
      fill.className = "bar-fill";
      fill.style.width = `${(ms / max) * 100}%`;
      track.appendChild(fill);
      const value = document.createElement("span");
      value.textContent = formatMinutes(ms);
      row.append(label, track, value);
      els.bars.appendChild(row);
    });

  els.sessions.innerHTML = "";
  if (!sessions.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "아직 이번 주말 기록이 없습니다.";
    els.sessions.appendChild(empty);
  } else {
    const list = document.createElement("ol");
    list.className = "sessions";
    sessions.slice(0, 8).forEach((session) => {
      const li = document.createElement("li");
      li.className = "session";
      const when = new Date(session.endedAt).toLocaleString("ko-KR", {
        weekday: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
      const label = document.createElement("span");
      label.textContent = `${session.name} · ${formatMinutes(session.actualMs)}`;
      const time = document.createElement("time");
      time.textContent = when;
      li.append(label, time);
      list.appendChild(li);
    });
    els.sessions.appendChild(list);
  }
  els.clear.hidden = sessions.length === 0;
}

function showToast(message) {
  els.toast.hidden = false;
  els.toast.textContent = message;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    els.toast.hidden = true;
  }, 2400);
}

function playChime() {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const now = ctx.currentTime;
  [523.25, 659.25, 783.99].forEach((freq, index) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.08, now + 0.02 + index * 0.08);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.8 + index * 0.08);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now + index * 0.08);
    osc.stop(now + 1);
  });
}

function tick() {
  if (!state.running) return;
  if (!isStopwatch() && elapsedMs() >= durationMs()) {
    finishTimer();
    return;
  }
  renderClock();
  state.raf = requestAnimationFrame(tick);
}

function start() {
  if (state.completed) reset(false);
  state.running = true;
  state.anchorTs = Date.now();
  renderClock();
  cancelAnimationFrame(state.raf);
  state.raf = requestAnimationFrame(tick);
}

function pause() {
  state.accumulatedMs = elapsedMs();
  state.running = false;
  cancelAnimationFrame(state.raf);
  renderClock();
}

function reset(announce = true) {
  state.running = false;
  state.accumulatedMs = 0;
  state.anchorTs = 0;
  state.completed = false;
  cancelAnimationFrame(state.raf);
  renderClock();
  if (announce) showToast("타이머를 리셋했습니다.");
}

function recordSession(actualMs, completed) {
  const activity = selected();
  if (actualMs < 1000) return;
  state.sessions.push({
    id: crypto.randomUUID(),
    activityId: activity.id,
    name: activity.name,
    plannedMs: durationMs(activity),
    actualMs,
    completed,
    endedAt: new Date().toISOString(),
  });
  save();
  renderSessions();
}

function finishTimer() {
  const actual = durationMs();
  state.running = false;
  state.accumulatedMs = actual;
  state.completed = true;
  cancelAnimationFrame(state.raf);
  recordSession(actual, true);
  renderClock();
  playChime();
  showToast(`${selected().name} ${selected().minutes}분 완료`);
}

function finishStopwatch() {
  const actual = elapsedMs();
  recordSession(actual, true);
  reset(false);
  playChime();
  showToast(`${selected().name} ${formatMinutes(actual)} 기록`);
}

function selectActivity(id) {
  if (state.running || state.accumulatedMs) {
    const ok = window.confirm("진행 중인 시간을 버리고 활동을 바꿀까요?");
    if (!ok) return;
  }
  state.selectedId = id;
  reset(false);
  renderActivities();
}

function addActivity(event) {
  event.preventDefault();
  const name = els.addName.value.trim();
  const minutes = Number(els.addMinutes.value);
  if (!name) return;
  const activity = {
    id: crypto.randomUUID(),
    name,
    minutes: Number.isFinite(minutes) ? Math.max(0, Math.min(180, minutes)) : 20,
  };
  state.activities.unshift(activity);
  state.selectedId = activity.id;
  save();
  els.addForm.hidden = true;
  els.addForm.reset();
  els.addMinutes.value = "20";
  renderActivities();
  reset(false);
}

function clearWeekend() {
  const { saturday, sunday } = weekendRange();
  state.sessions = state.sessions.filter((session) => {
    const date = new Date(session.endedAt);
    return date < saturday || date > sunday;
  });
  save();
  renderSessions();
}

function onKey(event) {
  if (event.target.matches("input")) return;
  if (event.code === "Space") {
    event.preventDefault();
    state.running ? pause() : start();
  }
  if (event.key.toLowerCase() === "r") reset();
}

function init() {
  load();
  if (!state.activities.length) state.activities = DEFAULT_ACTIVITIES.map((item) => ({ ...item }));
  if (!state.activities.some((item) => item.id === state.selectedId)) {
    state.selectedId = state.activities[0].id;
  }
  renderToday();
  renderActivities();
  renderClock();
  renderSessions();

  els.toggle.addEventListener("click", () => (state.running ? pause() : start()));
  els.reset.addEventListener("click", () => reset());
  els.done.addEventListener("click", finishStopwatch);
  els.addBtn.addEventListener("click", () => {
    els.addForm.hidden = !els.addForm.hidden;
    if (!els.addForm.hidden) els.addName.focus();
  });
  els.addCancel.addEventListener("click", () => {
    els.addForm.hidden = true;
  });
  els.addForm.addEventListener("submit", addActivity);
  els.clear.addEventListener("click", () => {
    if (window.confirm("이번 주말 기록을 모두 지울까요?")) clearWeekend();
  });
  document.addEventListener("keydown", onKey);
}

init();
