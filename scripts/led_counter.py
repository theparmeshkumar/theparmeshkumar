// Cloudflare Worker: wraps your existing working Komarev counter
// and renders it as a 7-segment LED SVG, white theme, on every real visit.
// No KV needed -- Komarev keeps doing the actual counting.

const USERNAME = "theparmeshkumar";
const W = 40, T = 6, H = 22, TOP_PAD = 14, LABEL_H = 22, LABEL_SIZE = 9;
const ON_COLOR = "#0506A1";
const OFF_COLOR = "#E5E7EB";
const BORDER_COLOR = "#0506A1";
const ACCENT_COLOR = "#FFD900";
const LABEL_COLOR = "#4B5563";
const LABEL = "PROFILE VISITORS";

const DIGIT_SEGMENTS = {
  "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd",
  "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
  "8": "abcdefg", "9": "abcdfg",
};

function hsegPoints(cx, cy, segW, t) {
  const halfW = segW / 2, halfT = t / 2, tip = halfT;
  const pts = [
    [cx - halfW, cy], [cx - halfW + tip, cy - halfT],
    [cx + halfW - tip, cy - halfT], [cx + halfW, cy],
    [cx + halfW - tip, cy + halfT], [cx - halfW + tip, cy + halfT],
  ];
  return pts.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
}

function vsegPoints(cx, cy, segH, t) {
  const halfH = segH / 2, halfT = t / 2, tip = halfT;
  const pts = [
    [cx, cy - halfH], [cx + halfT, cy - halfH + tip],
    [cx + halfT, cy + halfH - tip], [cx, cy + halfH],
    [cx - halfT, cy + halfH - tip], [cx - halfT, cy - halfH + tip],
  ];
  return pts.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
}

function digitSvg(digit, ox, oy) {
  const lit = DIGIT_SEGMENTS[digit] || "";
  const segs = {
    a: ["h", W / 2, 0], f: ["v", 0, H / 2], b: ["v", W, H / 2],
    g: ["h", W / 2, H], e: ["v", 0, H + H / 2], c: ["v", W, H + H / 2],
    d: ["h", W / 2, 2 * H],
  };
  let out = "";
  for (const [name, [orient, sx, sy]] of Object.entries(segs)) {
    const cx = ox + sx, cy = oy + sy;
    const color = lit.includes(name) ? ON_COLOR : OFF_COLOR;
    const pts = orient === "h"
      ? hsegPoints(cx, cy, W - T * 0.4, T)
      : vsegPoints(cx, cy, H - T * 0.4, T);
    out += `<polygon points="${pts}" fill="${color}"/>`;
  }
  return out;
}

function buildLedDisplay(numberStr) {
  const digitWidth = W + 22;
  const n = numberStr.length;
  const panelW = n * digitWidth + 50;
  const panelH = 2 * H + TOP_PAD + LABEL_H;

  let digitsSvg = "";
  for (let i = 0; i < n; i++) {
    digitsSvg += digitSvg(numberStr[i], 25 + i * digitWidth, TOP_PAD);
  }

  const defs = `
    <filter id="ledGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="1.6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="panelGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#FFFFFF"/>
    </linearGradient>
  `;

  return `<svg viewBox="0 0 ${panelW} ${panelH}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">
<defs>${defs}</defs>
<rect x="0" y="0" width="${panelW}" height="${panelH}" rx="10" fill="url(#panelGrad)" stroke="${BORDER_COLOR}" stroke-width="2.5"/>
<rect x="3" y="3" width="${panelW-6}" height="${panelH-6}" rx="7" fill="none" stroke="${ACCENT_COLOR}" stroke-width="1" opacity="0.6"/>
<g filter="url(#ledGlow)">
  <g>
    <animate attributeName="opacity" values="1;0.94;1;0.97;1" dur="4s" repeatCount="indefinite"/>
    ${digitsSvg}
  </g>
</g>
<text x="${panelW/2}" y="${panelH-6}" text-anchor="middle" fill="${LABEL_COLOR}" font-size="${LABEL_SIZE}" letter-spacing="2" font-weight="bold">${LABEL}</text>
</svg>`;
}

function fallbackDisplay(message) {
  // Renders a small readable placeholder instead of a broken image if Komarev is unreachable
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 60">
<rect width="260" height="60" rx="8" fill="#FFFFFF" stroke="#0506A1" stroke-width="2"/>
<text x="130" y="34" text-anchor="middle" fill="#4B5563" font-family="Arial" font-size="11">${message}</text>
</svg>`;
}

export default {
  async fetch(request) {
    try {
      const komarevUrl = `https://komarev.com/ghpvc/?username=${USERNAME}&style=flat`;
      // Forward the real visitor's request to Komarev right now -- this is what increments it,
      // exactly as it already does today, just triggered from here instead of directly from the README.
      const res = await fetch(komarevUrl, {
        headers: { "User-Agent": "Mozilla/5.0" },
        cf: { cacheTtl: 0, cacheEverything: false },
      });
      const svgText = await res.text();
      const matches = [...svgText.matchAll(/>([\d,]{2,})</g)];
      if (!matches.length) {
        return new Response(fallbackDisplay("Counter temporarily unavailable"), {
          headers: { "Content-Type": "image/svg+xml", "Cache-Control": "no-store" },
        });
      }
      const count = matches[matches.length - 1][1].replace(/,/g, "");
      const svg = buildLedDisplay(count);
      return new Response(svg, {
        headers: {
          "Content-Type": "image/svg+xml",
          "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
          "Pragma": "no-cache",
          "Expires": "0",
        },
      });
    } catch (err) {
      return new Response(fallbackDisplay("Counter temporarily unavailable"), {
        headers: { "Content-Type": "image/svg+xml", "Cache-Control": "no-store" },
      });
    }
  },
};
