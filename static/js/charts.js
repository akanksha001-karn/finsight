/* Tiny dependency-free chart helpers (canvas): barChart, lineChart, doughnutChart */
const PALETTE = ["#4f46e5","#10b981","#f59e0b","#ef4444","#06b6d4","#8b5cf6","#ec4899","#84cc16","#f97316","#14b8a6","#64748b"];

function setupCanvas(id) {
  const c = document.getElementById(id);
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth, h = c.clientHeight;
  c.width = w * dpr; c.height = h * dpr;
  const ctx = c.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.font = "12px Segoe UI, system-ui, sans-serif";
  return {ctx, w, h};
}
function short(n) { return n >= 100000 ? (n / 100000).toFixed(1) + "L" : n >= 1000 ? (n / 1000).toFixed(0) + "k" : String(Math.round(n)); }
function legend(id, items) {
  const el = document.getElementById(id + "-legend");
  if (el) el.innerHTML = items.map(i => `<span><i style="background:${i[1]}"></i>${i[0]}</span>`).join("");
}
function drawGrid(ctx, w, h, pad, max) {
  ctx.strokeStyle = "#e2e8f0"; ctx.fillStyle = "#94a3b8"; ctx.textAlign = "right"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (h - pad.t - pad.b) * i / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillText(short(max * (4 - i) / 4), pad.l - 6, y + 4);
  }
}
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); return Math.ceil(v / p) * p; }

function barChart(id, labels, datasets, opts = {}) {
  const {ctx, w, h} = setupCanvas(id);
  const pad = {l: 42, r: 10, t: 10, b: 26};
  const max = niceMax(Math.max(1, ...datasets.flatMap(d => d.data)));
  drawGrid(ctx, w, h, pad, max);
  const gw = (w - pad.l - pad.r) / labels.length, bw = Math.min(28, gw * 0.7 / datasets.length);
  labels.forEach((lb, i) => {
    datasets.forEach((d, j) => {
      const bh = (h - pad.t - pad.b) * d.data[i] / max;
      const x = pad.l + gw * i + (gw - bw * datasets.length) / 2 + bw * j;
      ctx.fillStyle = d.color; ctx.fillRect(x, h - pad.b - bh, bw - 2, bh);
    });
    if (!opts.sparseLabels || i % 5 === 0 || i === labels.length - 1) {
      ctx.fillStyle = "#64748b"; ctx.textAlign = "center"; ctx.fillText(lb, pad.l + gw * i + gw / 2, h - 8);
    }
  });
  if (!opts.hideLegend) legend(id, datasets.map(d => [d.label, d.color]));
}

function lineChart(id, labels, datasets) {
  const {ctx, w, h} = setupCanvas(id);
  const pad = {l: 42, r: 34, t: 10, b: 26};
  const max = niceMax(Math.max(1, ...datasets.flatMap(d => d.data.filter(v => v !== null))));
  drawGrid(ctx, w, h, pad, max);
  const step = (w - pad.l - pad.r) / Math.max(1, labels.length - 1);
  const X = i => pad.l + step * i, Y = v => h - pad.b - (h - pad.t - pad.b) * v / max;
  labels.forEach((lb, i) => { ctx.fillStyle = "#64748b"; ctx.textAlign = "center"; ctx.fillText(lb, X(i), h - 8); });
  datasets.forEach(d => {
    ctx.strokeStyle = d.color; ctx.fillStyle = d.color; ctx.lineWidth = 2.4;
    ctx.setLineDash(d.dashed ? [7, 5] : []); ctx.beginPath();
    let started = false;
    d.data.forEach((v, i) => { if (v === null) return; started ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)); started = true; });
    ctx.stroke(); ctx.setLineDash([]);
    d.data.forEach((v, i) => { if (v === null) return; ctx.beginPath(); ctx.arc(X(i), Y(v), d.dashed ? 4.5 : 3.2, 0, 7); d.dashed ? (ctx.fillStyle = "#fff", ctx.fill(), ctx.stroke()) : ctx.fill(); });
  });
  legend(id, datasets.map(d => [d.label, d.color]));
}

function doughnutChart(id, labels, data) {
  const {ctx, w, h} = setupCanvas(id);
  const total = data.reduce((a, b) => a + b, 0);
  if (!total) { ctx.fillStyle = "#94a3b8"; ctx.textAlign = "center"; ctx.fillText("No expense data this month", w / 2, h / 2); return; }
  const cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 8;
  let a = -Math.PI / 2;
  data.forEach((v, i) => {
    const s = v / total * Math.PI * 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, a, a + s); ctx.closePath();
    ctx.fillStyle = PALETTE[i % PALETTE.length]; ctx.fill(); a += s;
  });
  ctx.beginPath(); ctx.arc(cx, cy, R * 0.58, 0, 7); ctx.fillStyle = "#fff"; ctx.fill();
  ctx.fillStyle = "#1e293b"; ctx.textAlign = "center"; ctx.font = "bold 16px Segoe UI, sans-serif"; ctx.fillText("₹" + short(total), cx, cy + 5);
  legend(id, labels.map((l, i) => [`${l} (${Math.round(data[i] / total * 100)}%)`, PALETTE[i % PALETTE.length]]));
}
