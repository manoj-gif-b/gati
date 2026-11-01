const API = "";

let state = {
  studentId: null,
  subject: "maths",
  currentSkillId: null,
  lastNextStep: null,
  testSkillId: null,
  testItems: [],
  testAnswers: {},
  testSubmitted: false,
};

const loginScreen = document.getElementById("login-screen");
const app = document.getElementById("app");
const studentPicker = document.getElementById("student-picker");
const startBtn = document.getElementById("start-btn");
const loginErr = document.getElementById("login-err");
const themeToggle = document.getElementById("theme-toggle");
const subjButtons = document.querySelectorAll(".subj-btn");
const tabs = document.querySelectorAll(".tab");
const screens = {
  learn: document.getElementById("learn-screen"),
  solve: document.getElementById("solve-screen"),
  test: document.getElementById("test-screen"),
};

function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.add("hidden"));
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.screen === name));
  screens[name].classList.remove("hidden");
}

function setSubjectActive(subject) {
  subjButtons.forEach((b) =>
    b.classList.toggle("active", b.dataset.subject === subject)
  );
}

function applyTheme(theme) {
  if (theme === "light") {
    document.body.setAttribute("data-theme", "light");
    themeToggle.textContent = "Dark";
  } else {
    document.body.removeAttribute("data-theme");
    themeToggle.textContent = "Light";
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem("gati_theme", theme);
  } catch (e) {
    // Storage failed; fall back to dark theme.
    applyTheme("dark");
  }
}

themeToggle.addEventListener("click", () => {
  const isLight = document.body.hasAttribute("data-theme");
  if (isLight) {
    applyTheme("dark");
    saveTheme("dark");
  } else {
    applyTheme("light");
    saveTheme("light");
  }
});

async function loadStudents() {
  try {
    const r = await fetch("/api/students");
    if (!r.ok) throw new Error("could not load students (" + r.status + ")");
    const students = await r.json();
    studentPicker.innerHTML = "";
    for (const s of students) {
      const o = document.createElement("option");
      o.value = s.student_id;
      o.textContent = s.name + " (" + s.class + ", Class " + s.grade + ")";
      studentPicker.appendChild(o);
    }
  } catch (e) {
    loginErr.textContent = "Could not load students: " + e.message;
    console.error("loadStudents error:", e);
  }
}

startBtn.addEventListener("click", async () => {
  const id = +studentPicker.value;
  if (!id) {
    loginErr.textContent = "Pick a student";
    return;
  }
  state.studentId = id;
  localStorage.setItem("gati_student_id", String(id));
  loginScreen.classList.add("hidden");
  app.classList.remove("hidden");
  state.subject = "maths";
  setSubjectActive("maths");
  showScreen("learn");
  try {
    await renderLearn("maths");
  } catch (e) {
    const empty = document.getElementById("learn-empty");
    empty.classList.remove("hidden");
    empty.textContent = "Could not start lesson: " + e.message;
    console.error("start error:", e);
  }
});

subjButtons.forEach((b) => {
  b.addEventListener("click", () => {
    state.subject = b.dataset.subject;
    setSubjectActive(state.subject);
    showScreen("learn");
    renderLearn(state.subject);
  });
});

async function renderLearn(subject) {
  const card = document.getElementById("learn-card");
  const loading = document.getElementById("learn-loading");
  const empty = document.getElementById("learn-empty");
  const title = document.getElementById("learn-skill-title");
  const sub = document.getElementById("learn-skill-sub");
  const reason = document.getElementById("learn-reason");
  const concept = document.getElementById("learn-concept");

  card.classList.remove("hidden");
  loading.classList.remove("hidden");
  empty.classList.add("hidden");
  title.classList.add("hidden");
  sub.classList.add("hidden");
  reason.classList.add("hidden");
  concept.classList.add("hidden");

  try {
    const r = await fetch(
      "/api/students/" + state.studentId + "/next?subject=" + encodeURIComponent(subject)
    );
    if (!r.ok) throw new Error("next step failed (" + r.status + ")");
    const data = await r.json();
    state.currentSkillId = data.skill_id;
    state.lastNextStep = data;

    loading.classList.add("hidden");
    title.classList.remove("hidden");
    sub.classList.remove("hidden");
    title.textContent = data.name;
    sub.textContent = "Class " + data.grade + "  \u00b7  " + data.subject;
    reason.textContent = data.reason;
    reason.classList.remove("hidden");

    const sr = await fetch("/api/skills?subject=" + encodeURIComponent(subject));
    if (!sr.ok) throw new Error("skills fetch failed (" + sr.status + ")");
    const skills = await sr.json();
    const sk = skills.find((s) => s.skill_id === data.skill_id);
    const c = sk && sk.concept ? sk.concept : { title: data.name, text: "" };
    concept.innerHTML = "<strong>" + c.title + "</strong>" +
      (c.text ? "<p>" + c.text + "</p>" : "");
    concept.classList.remove("hidden");
  } catch (e) {
    loading.classList.add("hidden");
    empty.classList.remove("hidden");
    empty.textContent = "Could not load lesson: " + e.message;
    console.error("renderLearn error:", e);
  }
}

document.getElementById("learn-continue").addEventListener("click", () => {
  showScreen("solve");
  renderSolveCurrent();
});

async function renderSolveCurrent() {
  if (!state.currentSkillId) {
    document.getElementById("solve-empty").classList.remove("hidden");
    document.getElementById("solve-card").classList.add("hidden");
    return;
  }
  await fetchItemAndShow(state.currentSkillId, "solve", false);
}

async function fetchItemAndShow(skillId, target, isTest) {
  const card = target === "solve"
    ? document.getElementById("solve-card")
    : document.getElementById("test-card");
  const empty = target === "solve" ? document.getElementById("solve-empty") : null;
  const questionEl = target === "solve"
    ? document.getElementById("solve-question")
    : document.getElementById("test-question");
  const optionsEl = target === "solve"
    ? document.getElementById("solve-options")
    : document.getElementById("test-options");
  const feedbackEl = target === "solve"
    ? document.getElementById("solve-feedback")
    : document.getElementById("test-feedback");
  const continueBtn = target === "solve"
    ? document.getElementById("solve-continue")
    : document.getElementById("test-continue");

  if (empty) empty.classList.add("hidden");
  card.classList.remove("hidden");
  feedbackEl.textContent = "";
  feedbackEl.className = "feedback";
  continueBtn.classList.add("hidden");
  optionsEl.innerHTML = "";
  questionEl.textContent = "Loading...";

  try {
    const r = await fetch(
      "/api/items/next?student_id=" + state.studentId +
      "&skill_id=" + encodeURIComponent(skillId) +
      "&test=" + isTest
    );
    if (!r.ok) throw new Error("could not load item");
    const item = await r.json();
    state.currentItemId = item.id;
    if (target === "test" && isTest) state.testSkillId = skillId;
    questionEl.textContent = item.question;
    optionsEl.innerHTML = "";
    for (const opt of item.options) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = opt;
      btn.addEventListener("click", function() { handleAnswer(target, item, opt); });
      optionsEl.appendChild(btn);
    }
  } catch (e) {
    questionEl.textContent = "Could not load question: " + e.message;
  }
}
async function handleAnswer(target, item, answer) {
  const optionsEl = target === "solve"
    ? document.getElementById("solve-options")
    : document.getElementById("test-options");
  Array.from(optionsEl.children).forEach((b) => (b.disabled = true));

  const started = Date.now();
  try {
    const r = await fetch("/api/attempts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: state.studentId,
        item_id: item.id,
        answer: answer,
        time_taken_s: (Date.now() - started) / 1000,
      }),
    });
    if (!r.ok) throw new Error("answer rejected");
    const result = await r.json();

    const feedbackEl = target === "solve"
      ? document.getElementById("solve-feedback")
      : document.getElementById("test-feedback");
    feedbackEl.textContent = result.correct ? "Correct!" : "Incorrect.";
    feedbackEl.className = "feedback " + (result.correct ? "correct" : "incorrect");

    const pct = Math.round(result.mastery * 100);
    if (target === "solve") {
      document.getElementById("solve-mastery-fill").style.width = pct + "%";
      document.getElementById("solve-mastery-pct").textContent = pct + "%";
      state.lastNextStep = result.next_step;
      document.getElementById("solve-next-reason").textContent = result.next_step.reason;
      document.getElementById("solve-next-reason").classList.remove("hidden");

      if (result.test_required) {
        showScreen("test");
        await renderTestForSkill(state.currentSkillId);
        return;
      }
    }

    document.getElementById(target === "solve" ? "solve-continue" : "test-continue").classList.remove("hidden");
  } catch (e) {
    alert("Could not submit answer: " + e.message);
  } finally {
    Array.from(optionsEl.children).forEach((b) => (b.disabled = false));
  }
}

document.getElementById("solve-continue").addEventListener("click", () => {
  const action = state.lastNextStep ? state.lastNextStep.action : "practice";
  if (action === "practice") {
    renderSolveCurrent();
  } else {
    showScreen("learn");
    renderLearn(state.subject);
  }
});

tabs.forEach((t) => {
  t.addEventListener("click", () => {
    const name = t.dataset.screen;
    showScreen(name);
    if (name === "learn") renderLearn(state.subject);
    else if (name === "solve") renderSolveCurrent();
  });
});

async function renderTestForSkill(skillId) {
  const card = document.getElementById("test-card");
  const questionEl = document.getElementById("test-question");
  const optionsEl = document.getElementById("test-options");
  const feedbackEl = document.getElementById("test-feedback");
  const continueBtn = document.getElementById("test-continue");
  const skillLabel = document.getElementById("test-skill-label");

  try {
    const sr = await fetch("/api/skills?subject=" + encodeURIComponent(state.subject));
    const skills = await sr.json();
    const sk = skills.find((s) => s.skill_id === skillId);
    if (sk) skillLabel.textContent = "Mastery check: " + sk.name;
  } catch (e) {}

  card.classList.remove("hidden");
  feedbackEl.textContent = "";
  feedbackEl.className = "feedback";
  continueBtn.classList.add("hidden");
  optionsEl.innerHTML = "";
  questionEl.textContent = "Loading mastery check questions...";

  state.testSkillId = skillId;
  state.testItems = [];
  state.testAnswers = {};
  state.testSubmitted = false;

  try {
    const r = await fetch(
      "/api/tests/" + encodeURIComponent(skillId) + "/items?student_id=" + state.studentId
    );
    if (!r.ok) throw new Error("no test items available");
    const items = await r.json();
    state.testItems = items;
    showTestQuestion(0);
  } catch (e) {
    questionEl.textContent = "Could not load test: " + e.message;
  }
}

function showTestQuestion(index) {
  const questionEl = document.getElementById("test-question");
  const optionsEl = document.getElementById("test-options");
  const feedbackEl = document.getElementById("test-feedback");
  const continueBtn = document.getElementById("test-continue");

  if (index >= state.testItems.length) {
    questionEl.textContent = "All questions answered. Submit your answers.";
    optionsEl.innerHTML = "";
    const submitBtn = document.createElement("button");
    submitBtn.textContent = "Submit Mastery Check";
    submitBtn.addEventListener("click", submitTest);
    optionsEl.appendChild(submitBtn);
    feedbackEl.textContent = "";
    continueBtn.classList.add("hidden");
    return;
  }

  const item = state.testItems[index];
  questionEl.textContent = "Question " + (index + 1) + " of " + state.testItems.length + ": " + item.question;
  optionsEl.innerHTML = "";
  for (const opt of item.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = opt;
    if (state.testAnswers[item.id] === opt) btn.classList.add("active");
    btn.addEventListener("click", () => {
      state.testAnswers[item.id] = opt;
      Array.from(optionsEl.children).forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("test-continue").classList.remove("hidden");
    });
    optionsEl.appendChild(btn);
  }
  feedbackEl.textContent = "";
  continueBtn.classList.add("hidden");
}

async function submitTest() {
  if (state.testSubmitted) return;
  const unanswered = state.testItems.filter((it) => !(it.id in state.testAnswers));
  if (unanswered.length > 0) {
    alert("Please answer all 3 questions before submitting.");
    return;
  }

  state.testSubmitted = true;
  const optionsEl = document.getElementById("test-options");
  const feedbackEl = document.getElementById("test-feedback");
  const continueBtn = document.getElementById("test-continue");
  Array.from(optionsEl.children).forEach((b) => (b.disabled = true));

  try {
    const r = await fetch("/api/tests/" + encodeURIComponent(state.testSkillId) + "/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: state.studentId,
        answers: state.testItems.map((it) => ({
          item_id: it.id,
          answer: state.testAnswers[it.id],
        })),
      }),
    });
    if (!r.ok) throw new Error("test submit failed");
    const result = await r.json();

    feedbackEl.textContent = result.passed
      ? "Mastery check PASSED! Score: " + result.score + "/3. Skill confirmed mastered."
      : "Mastery check NOT PASSED. Score: " + result.score + "/3. Mastery reset \u2014 revisit the basics.";
    feedbackEl.className = "feedback " + (result.passed ? "correct" : "incorrect");

    state.lastNextStep = result.next_step;
    continueBtn.textContent = result.passed ? "Continue" : "Review basics";
    continueBtn.classList.remove("hidden");
  } catch (e) {
    alert("Could not submit test: " + e.message);
  } finally {
    Array.from(optionsEl.children).forEach((b) => (b.disabled = false));
  }
}

document.getElementById("test-continue").addEventListener("click", () => {
  if (state.testSubmitted) {
    const action = state.lastNextStep ? state.lastNextStep.action : "practice";
    if (action === "practice") {
      showScreen("solve");
      renderSolveCurrent();
    } else {
      showScreen("learn");
      renderLearn(state.subject);
    }
  } else {
    // Advance to the next test question before submission.
    showTestQuestion(Object.keys(state.testAnswers).length);
  }
});

(function boot() {
  const savedTheme = localStorage.getItem("gati_theme");
  applyTheme(savedTheme || "dark");

  const saved = localStorage.getItem("gati_student_id");
  if (saved) {
    state.studentId = +saved;
    loginScreen.style.display = "none";
    app.style.display = "block";
    state.subject = "maths";
    setSubjectActive("maths");
    showScreen("learn");
    loadStudents()
      .then(() => renderLearn(state.subject))
      .catch((e) => {
        loginScreen.classList.remove("hidden");
        app.classList.add("hidden");
        loginErr.textContent = "Could not load students: " + e.message;
        console.error("boot error:", e);
      });
  } else {
    loginScreen.classList.remove("hidden");
    app.classList.add("hidden");
    loadStudents();
  }
})();
