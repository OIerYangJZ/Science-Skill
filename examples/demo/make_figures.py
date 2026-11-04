#!/usr/bin/env python3
"""Draw the synthetic demo figures as SVG (standard library only). The data are invented for the demo."""
import os

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "figures")
COL = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]


def axes(w, h, xs, ys, xlabel, ylabel, title=""):
    m = dict(l=78, r=24, t=34, b=62)
    pw, ph = w - m["l"] - m["r"], h - m["t"] - m["b"]
    x0, x1 = xs
    y0, y1 = ys

    def X(v):
        return m["l"] + (v - x0) / (x1 - x0) * pw

    def Y(v):
        return m["t"] + ph - (v - y0) / (y1 - y0) * ph
    g = [f'<rect x="0" y="0" width="{w}" height="{h}" fill="white"/>',
         f'<line x1="{m["l"]}" y1="{m["t"] + ph}" x2="{m["l"] + pw}" y2="{m["t"] + ph}" stroke="#333" stroke-width="1.5"/>',
         f'<line x1="{m["l"]}" y1="{m["t"]}" x2="{m["l"]}" y2="{m["t"] + ph}" stroke="#333" stroke-width="1.5"/>']
    for i in range(6):
        yv = y0 + (y1 - y0) * i / 5
        g.append(f'<line x1="{m["l"]}" y1="{Y(yv):.1f}" x2="{m["l"] + pw}" y2="{Y(yv):.1f}" stroke="#E5E5E5"/>')
        g.append(f'<text x="{m["l"] - 10}" y="{Y(yv) + 6:.1f}" font-size="17" text-anchor="end">{yv:g}</text>')
    g.append(f'<text x="{m["l"] + pw / 2}" y="{h - 16}" font-size="19" text-anchor="middle">{xlabel}</text>')
    g.append(f'<text x="22" y="{m["t"] + ph / 2}" font-size="19" text-anchor="middle" '
             f'transform="rotate(-90 22 {m["t"] + ph / 2})">{ylabel}</text>')
    if title:
        g.append(f'<text x="{m["l"]}" y="22" font-size="19" font-weight="bold">{title}</text>')
    return g, X, Y, m, pw, ph


def curve():
    w, h = 900, 560
    g, X, Y, m, pw, ph = axes(w, h, (0, 50), (0.5, 1.0), "training epoch", "validation accuracy")
    for i in range(0, 51, 10):
        g.append(f'<text x="{X(i):.1f}" y="{m["t"] + ph + 26}" font-size="17" text-anchor="middle">{i}</text>')
    series = {"baseline": [0.52 + 0.30 * (1 - 0.92 ** e) for e in range(51)],
              "new loss": [0.52 + 0.38 * (1 - 0.90 ** e) for e in range(51)]}
    for k, (name, ys) in enumerate(series.items()):
        pts = " ".join(f"{X(e):.1f},{Y(v):.1f}" for e, v in enumerate(ys))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{COL[k]}" stroke-width="4"/>')
        g.append(f'<text x="{X(50) - 6:.1f}" y="{Y(ys[-1]) - 12:.1f}" font-size="19" fill="{COL[k]}" '
                 f'text-anchor="end" font-weight="bold">{name}</text>')
    return w, h, g


def bars():
    w, h = 900, 560
    vals = [("baseline", 0.812), ("+ augment", 0.846), ("+ new loss", 0.893), ("both", 0.901)]
    g, X, Y, m, pw, ph = axes(w, h, (0, len(vals)), (0.7, 0.95), "", "accuracy (5 seeds)")
    bw = pw / len(vals) * 0.6
    for i, (name, v) in enumerate(vals):
        cx = X(i + 0.5)
        g.append(f'<rect x="{cx - bw / 2:.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{Y(0.7) - Y(v):.1f}" '
                 f'fill="{COL[i % 4]}"/>')
        g.append(f'<text x="{cx:.1f}" y="{Y(v) - 8:.1f}" font-size="18" text-anchor="middle">{v:.3f}</text>')
        g.append(f'<text x="{cx:.1f}" y="{m["t"] + ph + 28}" font-size="18" text-anchor="middle">{name}</text>')
    return w, h, g


def pipeline():
    w, h = 1200, 300
    g = [f'<rect x="0" y="0" width="{w}" height="{h}" fill="white"/>']
    steps = ["raw images", "noise model", "denoiser", "evaluation"]
    for i, s in enumerate(steps):
        x = 30 + i * 295
        g.append(f'<rect x="{x}" y="90" width="230" height="120" rx="16" fill="{COL[i]}" opacity="0.9"/>')
        g.append(f'<text x="{x + 115}" y="160" font-size="26" fill="white" text-anchor="middle" '
                 f'font-weight="bold">{s}</text>')
        if i < 3:
            g.append(f'<path d="M{x + 238} 150 L{x + 287} 150" stroke="#333" stroke-width="4" '
                     f'marker-end="url(#a)"/>')
    g.insert(0, '<defs><marker id="a" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto">'
                '<path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker></defs>')
    return w, h, g


def save(name, fig):
    w, h, g = fig
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'font-family="Arial, Helvetica, sans-serif">' + "".join(g) + "</svg>\n")
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(svg)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    save("learning_curve.svg", curve())
    save("ablation.svg", bars())
    save("pipeline.svg", pipeline())
    print("wrote", OUT)
