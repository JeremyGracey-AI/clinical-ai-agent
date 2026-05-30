/* Zero-dependency SVG charts for the Work IQ panel + analytics.
   Exposed as window.Charts. */
window.Charts = (function () {
  const C = { accent: "#34d399", accent2: "#38bdf8", warn: "#fbbf24", danger: "#f87171",
              line: "#26344f", muted: "#93a4bf" };

  const color = (v01) => (v01 >= 0.8 ? C.accent : v01 >= 0.5 ? C.warn : C.danger);

  // --- semicircle gauge, value in [0,100] ---
  function gauge(value) {
    const cx = 90, cy = 84, r = 66, sw = 13;
    const f = Math.max(0, Math.min(100, value)) / 100;
    const pt = (t) => { const a = Math.PI - t * Math.PI; return [cx + r * Math.cos(a), cy - r * Math.sin(a)]; };
    const arc = (t0, t1) => {
      const [x0, y0] = pt(t0), [x1, y1] = pt(t1);
      return `M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 ${t1 - t0 > 0.5 ? 1 : 0} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
    };
    return `<svg viewBox="0 0 180 100" width="180" height="100">
      <path d="${arc(0, 1)}" fill="none" stroke="#0e1729" stroke-width="${sw}" stroke-linecap="round"/>
      <path d="${arc(0, f)}" fill="none" stroke="${color(f)}" stroke-width="${sw}" stroke-linecap="round"/>
      <text x="${cx}" y="${cy - 6}" text-anchor="middle" fill="#e6edf6" font-size="30" font-weight="700">${value}</text>
      <text x="${cx}" y="${cy + 12}" text-anchor="middle" fill="${C.muted}" font-size="11">/ 100 Work IQ</text>
    </svg>`;
  }

  // --- radar, axes = [{label, value 0..1}] ---
  function radar(axes) {
    const cx = 112, cy = 104, R = 64, n = axes.length;
    const ang = (i) => -Math.PI / 2 + i * (2 * Math.PI / n);
    const at = (i, rad) => [cx + rad * Math.cos(ang(i)), cy + rad * Math.sin(ang(i))];
    const poly = (rad, fn) => axes.map((_, i) => { const [x, y] = (fn || at)(i, rad); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(" ");

    let g = "";
    [0.25, 0.5, 0.75, 1].forEach((ring) =>
      g += `<polygon points="${poly(R * ring)}" fill="none" stroke="${C.line}" stroke-width="1"/>`);
    axes.forEach((_, i) => { const [x, y] = at(i, R); g += `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${C.line}"/>`; });

    const vpts = axes.map((a, i) => at(i, R * Math.max(0, Math.min(1, a.value)))).map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    g += `<polygon points="${vpts}" fill="${C.accent}33" stroke="${C.accent}" stroke-width="2"/>`;
    axes.forEach((a, i) => { const [x, y] = at(i, R * Math.max(0, Math.min(1, a.value))); g += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6" fill="${C.accent}"/>`; });

    axes.forEach((a, i) => {
      const [x, y] = at(i, R + 16);
      const anchor = Math.abs(x - cx) < 6 ? "middle" : x > cx ? "start" : "end";
      g += `<text x="${x.toFixed(1)}" y="${(y + 3).toFixed(1)}" text-anchor="${anchor}" fill="${C.muted}" font-size="10.5">${a.label}</text>`;
    });
    return `<svg viewBox="0 0 224 208" width="224" height="208">${g}</svg>`;
  }

  // --- sparkline of numeric values ---
  function sparkline(values) {
    if (!values.length) return `<svg viewBox="0 0 300 60" width="100%" height="60"></svg>`;
    const W = 300, H = 60, pad = 6;
    const lo = Math.min(...values, 0), hi = Math.max(...values, 100);
    const x = (i) => pad + (values.length === 1 ? 0 : i * (W - 2 * pad) / (values.length - 1));
    const y = (v) => H - pad - (v - lo) / (hi - lo || 1) * (H - 2 * pad);
    const pts = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const last = values[values.length - 1];
    const area = `${pad},${H - pad} ${pts} ${x(values.length - 1).toFixed(1)},${H - pad}`;
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="60" preserveAspectRatio="none">
      <polygon points="${area}" fill="${C.accent}1a"/>
      <polyline points="${pts}" fill="none" stroke="${C.accent}" stroke-width="2"/>
      <circle cx="${x(values.length - 1).toFixed(1)}" cy="${y(last).toFixed(1)}" r="3" fill="${C.accent}"/>
    </svg>`;
  }

  return { gauge, radar, sparkline };
})();
