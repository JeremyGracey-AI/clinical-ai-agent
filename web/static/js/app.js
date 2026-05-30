/* Clinical AI Agent dashboard — fetches patients, streams a run, renders panels. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  // illustrative abnormal thresholds (display only — mirrors agents/study_plan RULES)
  const HOT = [[/a1c/i, (v) => v >= 8], [/egfr/i, (v) => v < 60], [/systolic|blood pressure/i, (v) => v >= 140], [/ldl/i, (v) => v >= 190]];
  const isHot = (label, v) => HOT.some(([re, fn]) => re.test(label) && fn(v));

  let patients = [], selected = "demo-1";

  async function boot() {
    try {
      const cfg = await (await fetch("/api/config")).json();
      const b = $("#backend-badge");
      b.textContent = `backend: ${cfg.backend}${cfg.offline ? " · offline" : ""}`;
    } catch (e) { /* badge is cosmetic */ }
    patients = await (await fetch("/api/patients")).json();
    renderPatients();
    $("#run-btn").addEventListener("click", run);
    $("#query").addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
    document.querySelectorAll(".tab").forEach((t) =>
      t.addEventListener("click", () => switchTab(t.dataset.tab)));
  }

  function renderPatients() {
    const rail = $("#patient-rail"); rail.innerHTML = "";
    patients.forEach((p) => {
      const card = el("div", "patient" + (p.id === selected ? " active" : ""));
      card.appendChild(el("div", "pname", p.name));
      card.appendChild(el("div", "pmeta", `${p.id} · ${p.gender || "—"} · DOB ${p.birth_date || "—"}`));
      const labs = el("div", "plabs");
      p.labs.forEach((l) => {
        const hot = l.value != null && isHot(l.label || "", l.value);
        labs.appendChild(el("span", "lab" + (hot ? " hot" : ""), `${l.label}: ${l.value}${l.unit ? " " + l.unit : ""}`));
      });
      card.appendChild(labs);
      card.addEventListener("click", () => { selected = p.id; renderPatients(); });
      rail.appendChild(card);
    });
  }

  function switchTab(name) {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    $("#tab-plan").hidden = name !== "plan";
    $("#tab-assess").hidden = name !== "assess";
  }

  async function run() {
    const btn = $("#run-btn");
    btn.disabled = true; btn.textContent = "Running…";
    $("#results").hidden = false;
    const ans = $("#answer-text"); ans.innerHTML = '<span class="caret"></span>';
    let acc = "";
    const body = JSON.stringify({ query: $("#query").value, patient_id: selected });
    try {
      const resp = await fetch("/api/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body });
      const reader = resp.body.getReader(); const dec = new TextDecoder(); let buf = "";
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const line = buf.slice(0, i); buf = buf.slice(i + 2);
          if (!line.startsWith("data: ")) continue;
          const msg = JSON.parse(line.slice(6));
          if (msg.delta) { acc += msg.delta; ans.innerHTML = ""; ans.appendChild(document.createTextNode(acc)); ans.appendChild(el("span", "caret")); }
          if (msg.done) { ans.textContent = msg.result.answer_text; render(msg.result); }
        }
      }
    } catch (e) {
      ans.textContent = "Error: " + e.message;
    } finally {
      btn.disabled = false; btn.textContent = "Run pipeline";
    }
  }

  function render(d) {
    // route + confidence
    const rb = $("#route-badge"); rb.className = "badge " + (d.route || ""); rb.textContent = "route: " + (d.route || "—");
    const cb = $("#confidence-badge"); cb.className = "badge " + (d.confidence || ""); cb.textContent = "confidence: " + (d.confidence || "—");

    // patient citations
    const pc = $("#patient-cites"); pc.innerHTML = "";
    (d.patient_citations || []).forEach((c) => {
      const chip = el("div", "chip");
      const b = el("b", null, c.label); chip.appendChild(b);
      chip.appendChild(document.createTextNode(` = ${c.value}${c.effective ? " @ " + c.effective.slice(0, 10) : ""}`));
      const r = el("div"); r.style.cssText = "font-size:11px;color:#7f93b8;margin-top:2px"; r.textContent = c.resource;
      chip.appendChild(r); pc.appendChild(chip);
    });

    // literature
    const lit = $("#literature"); lit.innerHTML = "";
    (d.literature || []).forEach((c) => {
      const ev = el("div", "ev");
      if (c.score != null) ev.appendChild(el("span", "score", c.score.toFixed ? c.score.toFixed(3) : c.score));
      ev.appendChild(el("span", "ev-src", c.source + " "));
      ev.appendChild(document.createTextNode(c.title));
      ev.appendChild(el("br"));
      const a = el("a", null, c.url); a.href = c.url; a.target = "_blank"; a.rel = "noopener"; ev.appendChild(a);
      lit.appendChild(ev);
    });

    // conditions
    const cg = $("#conditions"); cg.innerHTML = "";
    if (!(d.flagged_conditions || []).length) cg.appendChild(el("div", "empty", "No conditions flagged for this patient's current observations."));
    (d.flagged_conditions || []).forEach((f) => {
      const c = el("div", "cond");
      c.appendChild(el("div", "ctitle", f.condition));
      c.appendChild(el("div", "ctrig", "trigger: " + f.trigger));
      cg.appendChild(c);
    });

    // study plan
    const tp = $("#tab-plan"); tp.innerHTML = "";
    if (!(d.study_plan || []).length) tp.appendChild(el("div", "empty", "No modules."));
    (d.study_plan || []).forEach((m) => {
      const mod = el("div", "module");
      const top = el("div", "mtop");
      top.appendChild(el("span", "mtopic", `${m.order}. ${m.topic}`));
      top.appendChild(el("span", "pill", `${m.difficulty} · mastery ${m.mastery}`));
      mod.appendChild(top);
      mod.appendChild(el("div", "mobj", m.objective));
      const src = el("div", "mobj");
      src.appendChild(document.createTextNode("evidence: "));
      if (m.evidence_url) { const a = el("a", null, m.evidence_source || "source"); a.href = m.evidence_url; a.target = "_blank"; a.rel = "noopener"; src.appendChild(a); }
      else src.appendChild(document.createTextNode(m.evidence_source || "—"));
      mod.appendChild(src);
      tp.appendChild(mod);
    });

    // assessment
    const ta = $("#tab-assess"); ta.innerHTML = "";
    const items = (d.assessment && d.assessment.items) || [];
    if (!items.length) ta.appendChild(el("div", "empty", "No items."));
    items.forEach((it, idx) => {
      const m = el("div", "module");
      m.appendChild(el("div", "mq", `Q${idx + 1} (${it.topic}). ${it.question}`));
      (it.options || []).forEach((o, j) => m.appendChild(el("div", "opt" + (j === it.answer_index ? " correct" : ""), `${String.fromCharCode(65 + j)}. ${o}${j === it.answer_index ? "  ✓" : ""}`)));
      ta.appendChild(m);
    });

    // Work IQ
    const w = d.work_iq || {};
    $("#gauge").innerHTML = Charts.gauge(w.clinical_work_iq != null ? w.clinical_work_iq : 0);
    $("#radar").innerHTML = Charts.radar([
      { label: "faithful", value: w.faithfulness || 0 },
      { label: "citation", value: w.citation_coverage || 0 },
      { label: "recall", value: w.retrieval_recall || 0 },
      { label: "safety", value: w.safety_probe_recall || 0 },
    ]);
    const metrics = [
      ["Faithfulness", w.faithfulness], ["Citation coverage", w.citation_coverage],
      ["Retrieval precision", w.retrieval_precision], ["Retrieval recall", w.retrieval_recall],
      ["Safety-probe recall", w.safety_probe_recall],
    ];
    const mm = $("#metrics"); mm.innerHTML = "";
    metrics.forEach(([label, v]) => {
      v = v || 0;
      const row = el("div", "metric");
      row.appendChild(el("span", "mlabel", label));
      row.appendChild(el("span", "mval", v.toFixed ? v.toFixed(3) : v));
      const bar = el("div", "bar"); const i = el("i"); i.style.width = (v * 100) + "%"; bar.appendChild(i);
      row.appendChild(bar); mm.appendChild(row);
    });

    // session
    $("#digest").textContent = d.digest || "";
    const nu = $("#nudges"); nu.innerHTML = "";
    (d.nudges || []).forEach((n) => nu.appendChild(el("li", null, n)));

    // trace
    $("#trace-card").hidden = false;
    $("#trace").textContent = (d.trace || []).join("\n");

    // analytics
    fetch("/api/analytics").then((r) => r.json()).then((h) => {
      $("#sparkline").innerHTML = Charts.sparkline((h || []).map((r) => r.clinical_work_iq).filter((v) => v != null));
    }).catch(() => {});
  }

  boot();
})();
