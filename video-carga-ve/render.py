import math, subprocess, sys
import numpy as np, cairo, imageio_ffmpeg
from sim import t, N, DT, EVS, need, PMAX, TARGET, BAT, ORDER, uncontrolled, managed, CAP

W, H, FPS, DUR = 1080, 1920, 30, 30.0
FR = int(FPS * DUR)
U = uncontrolled(); M, _ = managed(CAP)
PEAK_U = U.sum(0).max(); PEAK_M = M.sum(0).max()
RANK = {int(v): r for r, v in enumerate(ORDER)}

def hexc(h, a=1.0):
    h = h.lstrip('#'); return (int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255, a)
BG1, BG2 = hexc('0B1D3A'), hexc('050E22')
GRID = hexc('1C3558'); TXT = hexc('EAF1FF'); MUTED = hexc('8193B5')
CYAN = hexc('3FD0E0'); RED = hexc('FF4B5C'); GOLD = hexc('F4B942')
VCOL = [hexc(c) for c in ('3FA9F5', '36C2B4', '8A7CFF', '5AD1F0', '6F8FD8')]
FONT = 'DejaVu Sans'

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return 4*x*x*x if x < .5 else 1 - (-2*x + 2)**3/2
def eout(x): x = clamp(x); return 1 - (1 - x)**3
def seg(s, a, b): return ease((s - a) / (b - a))
def lerp(a, b, p): return a + (b - a) * p
def lerpc(c1, c2, p): return tuple(lerp(x, y, p) for x, y in zip(c1, c2))
def rgba(ctx, c, a=1.0): ctx.set_source_rgba(c[0], c[1], c[2], c[3] * a)

def text(ctx, s, x, y, size, col, a=1.0, bold=False, align='l', spacing=0.0):
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    w = ctx.text_extents(s).x_advance + spacing * max(len(s) - 1, 0)
    if align == 'c': x -= w / 2
    elif align == 'r': x -= w
    rgba(ctx, col, a)
    if spacing:
        for ch in s:
            ctx.move_to(x, y); ctx.show_text(ch); x += ctx.text_extents(ch).x_advance + spacing
    else:
        ctx.move_to(x, y); ctx.show_text(s)

def rrect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi/2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi/2)
    ctx.arc(x + r, y + h - r, r, math.pi/2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5*math.pi)
    ctx.close_path()

def hhmm(h):
    h = h % 24; return f"{int(h):02d}:{int(round((h - int(h))*60)):02d}"
def kw(v): return f"{v:.1f}".replace('.', ',')

def car(ctx, cx, cy, col, a, charging, pulse):
    ctx.save(); ctx.translate(cx, cy)
    # body
    ctx.move_to(-62, 10); ctx.line_to(-62, -6); ctx.curve_to(-60, -14, -54, -16, -44, -17)
    ctx.line_to(-28, -34); ctx.curve_to(-24, -38, -18, -39, -12, -39); ctx.line_to(22, -39)
    ctx.curve_to(28, -39, 32, -37, 36, -33); ctx.line_to(50, -17); ctx.curve_to(58, -16, 62, -12, 62, -4)
    ctx.line_to(62, 10); ctx.close_path()
    rgba(ctx, col, 0.16 * a); ctx.fill_preserve(); rgba(ctx, col, a); ctx.set_line_width(3); ctx.stroke()
    # windows
    ctx.move_to(-38, -18); ctx.line_to(-24, -33); ctx.line_to(-4, -33); ctx.line_to(-4, -18); ctx.close_path()
    ctx.move_to(2, -18); ctx.line_to(2, -33); ctx.line_to(22, -33); ctx.line_to(35, -18); ctx.close_path()
    rgba(ctx, col, 0.45 * a); ctx.fill()
    for wx in (-36, 36):
        ctx.arc(wx, 11, 12, 0, 2*math.pi); rgba(ctx, BG2, a); ctx.fill_preserve()
        rgba(ctx, col, a); ctx.set_line_width(3); ctx.stroke()
        ctx.arc(wx, 11, 4, 0, 2*math.pi); rgba(ctx, col, a); ctx.fill()
    if charging > 0:
        g = 0.55 + 0.45 * math.sin(pulse)
        ctx.move_to(4, -62); ctx.line_to(-8, -44); ctx.line_to(0, -44); ctx.line_to(-4, -30)
        ctx.line_to(9, -50); ctx.line_to(1, -50); ctx.close_path()
        rgba(ctx, CYAN, a * charging * g); ctx.fill()
    ctx.restore()

# layout
MX = 64; BAY_W = (W - 2*MX) / 5
BAY_Y, BAY_H = 318, 400
CX0, CX1, CY0, CY1 = 150, 1010, 850, 1470
YMAX = 40.0
def X(h): return CX0 + (h - 17.0) / 15.0 * (CX1 - CX0)
def Y(p): return CY1 - p / YMAX * (CY1 - CY0)

# phase timings (seconds)
T_SWEEP_A = (2.0, 6.6)   # 17:00 -> 20:30, arrivals
T_SWEEP_B = (6.6, 9.2)   # 20:30 -> 08:00
T_PRIO = (11.2, 14.0)    # bays reorder by priority
T_MORPH0, T_MORPH_STEP, T_MORPH_LEN = 14.6, 1.25, 2.4
T_GOLD_SWEEP = (21.6, 25.2)
T_KPI = 25.0

def playhead1(s):
    if s < T_SWEEP_A[0]: return 17.0
    if s < T_SWEEP_A[1]: return lerp(17.0, 20.5, (s - T_SWEEP_A[0]) / (T_SWEEP_A[1] - T_SWEEP_A[0]))
    return lerp(20.5, 32.0, ease((s - T_SWEEP_B[0]) / (T_SWEEP_B[1] - T_SWEEP_B[0])))

def morph_p(i, s):
    return ease((s - (T_MORPH0 + RANK[i] * T_MORPH_STEP)) / T_MORPH_LEN)

def soc_at(P, i, h):
    k = int(clamp((h - 17.0) / DT, 0, N))
    return EVS[i][3] + P[i, :k].sum() * DT / BAT

def frame(s):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgba(0, *BG1); g.add_color_stop_rgba(1, *BG2)
    ctx.set_source(g); ctx.paint()
    # subtle tech dot grid
    for gy in range(40, H, 48):
        for gx in range(24, W, 48):
            ctx.new_sub_path(); ctx.arc(gx, gy, 1.2, 0, 2*math.pi)
    rgba(ctx, GRID, 0.55); ctx.fill()
    fade_in = eout(s / 1.2); fade_out = 1 - seg(s, 29.3, 30.0)
    A = fade_in * fade_out

    # ---- header
    text(ctx, 'GESTIÓN DE CARGA  ·  5 VEHÍCULOS', MX, 150, 26, CYAN, A, True, spacing=2.5)
    titles = [(0.0, 10.6, 'Carga sin gestión'), (10.6, 21.2, 'Prioridad: salida + SoC'), (21.2, 99, 'Carga gestionada')]
    for a0, a1, ttl in titles:
        al = seg(s, a0 - 0.3, a0 + 0.3) * (1 - seg(s, a1 - 0.3, a1 + 0.3)) if a0 > 0 else (1 - seg(s, a1 - 0.3, a1 + 0.3))
        if al > 0.01:
            col = RED if 'sin' in ttl else (GOLD if 'gestionada' in ttl else TXT)
            text(ctx, ttl, MX, 232 + (1 - al) * 14, 62, col, A * al, True)

    # ---- phase state
    ph = playhead1(s)
    in_phase1 = s < 10.6
    reset = seg(s, 10.4, 11.2)          # SoC bars rewind for re-planning
    gold_ph = lerp(17.0, 32.0, ease((s - T_GOLD_SWEEP[0]) / (T_GOLD_SWEEP[1] - T_GOLD_SWEEP[0])))
    prio = seg(s, *T_PRIO)
    pulse = s * 6.0

    # ---- bays
    for i in sorted(range(5), key=lambda j: abs(RANK[j] - j)):
        name, arr, dep, soc0 = EVS[i]
        slot = lerp(i, RANK[i], prio)
        bx = MX + slot * BAY_W + 6; bw = BAY_W - 12
        lift = -math.sin(math.pi * prio) * 30 * abs(RANK[i] - i)
        ctx.save(); ctx.translate(0, -lift)
        dock = eout((ph - arr) / 0.35) if s < 10.6 else 1.0
        dock = dock * clamp((s - T_SWEEP_A[0]) / 0.2) if s < 10.6 else 1.0
        rrect(ctx, bx, BAY_Y, bw, BAY_H, 18); rgba(ctx, hexc('0F2748'), A); ctx.fill_preserve()
        active = 0.0
        if s >= T_MORPH0: active = clamp((s - (T_MORPH0 + RANK[i]*T_MORPH_STEP)) / 0.3) * (1 - clamp((s - (T_MORPH0 + RANK[i]*T_MORPH_STEP + T_MORPH_LEN)) / 0.4))
        edge = lerpc(GRID, GOLD, active)
        rgba(ctx, edge, A); ctx.set_line_width(2 + 2*active); ctx.stroke()
        cx = bx + bw / 2
        # charger post
        rrect(ctx, cx - 9, BAY_Y + 22, 18, 30, 5); rgba(ctx, MUTED, 0.6 * A); ctx.fill()
        # current SoC & charging flag
        if in_phase1:
            soc = soc_at(U, i, ph) if ph >= arr else soc0
            chg = 1.0 if (ph >= arr and U[i, min(int((ph - 17)/DT), N-1)] > 0) else 0.0
        else:
            soc_end1 = soc_at(U, i, 32.0)
            if s < T_GOLD_SWEEP[0]:
                soc = lerp(soc_end1, soc0, reset); chg = 0.0
            else:
                soc = soc_at(M, i, gold_ph)
                k = min(int((gold_ph - 17)/DT), N-1)
                chg = 1.0 if (M[i, k] > 0.05 and gold_ph < 31.99) else 0.0
        ca = A * dock
        car(ctx, cx + (1 - dock) * -160, BAY_Y + 120, VCOL[i], ca, chg, pulse + i)
        text(ctx, name, cx, BAY_Y + 190, 30, TXT, ca, True, 'c')
        # SoC bar
        bxw = bw - 44; bx0 = cx - bxw/2; by = BAY_Y + 222
        rrect(ctx, bx0, by, bxw, 14, 7); rgba(ctx, GRID, ca); ctx.fill()
        fillc = GOLD if s >= T_GOLD_SWEEP[0] else VCOL[i]
        rrect(ctx, bx0, by, max(14, bxw * soc), 14, 7); rgba(ctx, fillc, ca); ctx.fill()
        ctx.move_to(bx0 + bxw*TARGET, by - 6); ctx.line_to(bx0 + bxw*TARGET, by + 20)
        rgba(ctx, TXT, 0.55*ca); ctx.set_line_width(2); ctx.stroke()
        text(ctx, f"{int(round(soc*100))} %", cx, by + 56, 28, TXT, ca, False, 'c')
        text(ctx, 'sale', cx, BAY_Y + 318, 22, MUTED, ca, False, 'c')
        text(ctx, hhmm(dep), cx, BAY_Y + 352, 30, TXT, ca, True, 'c')
        # priority badge
        if prio > 0 and s < 99:
            ba = A * clamp((s - T_PRIO[0]) / 0.6)
            rrect(ctx, cx - 26, BAY_Y - 22, 52, 40, 20); rgba(ctx, GOLD, ba); ctx.fill()
            text(ctx, str(RANK[i] + 1), cx, BAY_Y + 9, 26, BG2, ba, True, 'c')
        # done tick
        if s >= T_GOLD_SWEEP[0] and soc >= TARGET - 1e-3:
            ta = A * clamp((s - T_GOLD_SWEEP[0]) / 0.3)
            ctx.arc(bx + bw - 26, BAY_Y + 26, 14, 0, 2*math.pi); rgba(ctx, GOLD, ta); ctx.fill()
            ctx.move_to(bx + bw - 33, BAY_Y + 26); ctx.line_to(bx + bw - 28, BAY_Y + 31); ctx.line_to(bx + bw - 19, BAY_Y + 20)
            rgba(ctx, BG2, ta); ctx.set_line_width(3); ctx.stroke()
        ctx.restore()

    # ---- chart frame
    axa = A * seg(s, 0.2, 1.6)
    for v in (10, 20, 30, 40):
        ctx.move_to(CX0, Y(v)); ctx.line_to(CX0 + (CX1 - CX0) * axa, Y(v))
        rgba(ctx, GRID, axa); ctx.set_line_width(1.5); ctx.stroke()
        text(ctx, str(v), CX0 - 18, Y(v) + 8, 24, MUTED, axa, False, 'r')
    text(ctx, 'kW', CX0 - 18, CY0 - 36, 24, MUTED, axa, True, 'r')
    ctx.move_to(CX0, CY1); ctx.line_to(CX0 + (CX1 - CX0) * axa, CY1); rgba(ctx, MUTED, axa); ctx.set_line_width(2); ctx.stroke()
    for h in (17, 20, 23, 26, 29, 32):
        text(ctx, hhmm(h), X(h), CY1 + 44, 24, MUTED, axa, False, 'c')
    # arrival window 17-20 h
    wa = A * seg(s, 1.2, 2.2) * (1 - 0.6 * seg(s, 10.0, 11.0))
    ctx.rectangle(X(17), CY0 - 10, X(20) - X(17), CY1 - CY0 + 10); rgba(ctx, CYAN, 0.06 * wa); ctx.fill()
    text(ctx, 'llegadas', (X(17) + X(20)) / 2, CY0 - 22, 22, CYAN, 0.9 * wa, False, 'c')

    # ---- profiles for this instant
    if s < T_MORPH0:
        P = U.copy()
    else:
        P = np.array([lerp(U[i], M[i], morph_p(i, s)) for i in range(5)])
    mean_p = np.mean([morph_p(i, s) for i in range(5)]) if s >= T_MORPH0 else 0.0
    line_col = lerpc(RED, GOLD, mean_p)
    clip_h = ph if s < 10.6 else 32.0
    xs = X(t + DT/2)
    xs = np.concatenate([[X(17.0)], xs, [X(32.0)]])

    ctx.save(); ctx.rectangle(CX0 - 4, 0, X(clip_h) - CX0 + 4, H); ctx.clip()
    # ghost of uncontrolled curve once reorganisation starts
    if s >= T_MORPH0:
        ga = A * seg(s, T_MORPH0, T_MORPH0 + 1.5)
        tot = U.sum(0); ys = np.concatenate([[tot[0]], tot, [tot[-1]]])
        ctx.set_dash([10, 10]); ctx.move_to(xs[0], Y(ys[0]))
        for x, y in zip(xs[1:], ys[1:]): ctx.line_to(x, Y(y))
        rgba(ctx, RED, 0.45 * ga); ctx.set_line_width(2.5); ctx.stroke(); ctx.set_dash([])
    # stacked areas
    base = np.zeros(N)
    for i in range(5):
        top = base + P[i]
        tb = np.concatenate([[base[0]], base, [base[-1]]]); tt = np.concatenate([[top[0]], top, [top[-1]]])
        ctx.move_to(xs[0], Y(tt[0]))
        for x, y in zip(xs[1:], tt[1:]): ctx.line_to(x, Y(y))
        for x, y in zip(xs[::-1], tb[::-1]): ctx.line_to(x, Y(y))
        ctx.close_path(); rgba(ctx, VCOL[i], 0.30 * A); ctx.fill()
        base = top
    tot = P.sum(0); ys = np.concatenate([[tot[0]], tot, [tot[-1]]])
    for lw, al in ((16, 0.10), (9, 0.18), (4.5, 1.0)):
        ctx.move_to(xs[0], Y(ys[0]))
        for x, y in zip(xs[1:], ys[1:]): ctx.line_to(x, Y(y))
        rgba(ctx, line_col, al * A); ctx.set_line_width(lw); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()
    ctx.restore()

    # playhead
    if T_SWEEP_A[0] <= s < 9.6:
        pa = A * (1 - seg(s, 9.2, 9.6))
        ctx.move_to(X(ph), CY0 - 10); ctx.line_to(X(ph), CY1); rgba(ctx, CYAN, 0.8 * pa); ctx.set_line_width(2); ctx.stroke()
        text(ctx, hhmm(ph), X(ph), CY1 + 80, 26, CYAN, pa, True, 'c')
    if T_GOLD_SWEEP[0] <= s < T_GOLD_SWEEP[1] + 0.4:
        pa = A * (1 - seg(s, T_GOLD_SWEEP[1], T_GOLD_SWEEP[1] + 0.4))
        ctx.move_to(X(gold_ph), CY0 - 10); ctx.line_to(X(gold_ph), CY1); rgba(ctx, GOLD, 0.8 * pa); ctx.set_line_width(2); ctx.stroke()
        text(ctx, hhmm(gold_ph), X(gold_ph), CY1 + 80, 26, GOLD, pa, True, 'c')

    # peak marker
    pk = int(U.sum(0).argmax()); pa = A * seg(s, 8.6, 9.4) * (1 - seg(s, T_MORPH0 - 0.2, T_MORPH0 + 0.8))
    if pa > 0.01:
        px, py = X(t[pk] + DT/2), Y(PEAK_U)
        r = 14 + 10 * (0.5 + 0.5 * math.sin(s * 5))
        ctx.arc(px, py, r, 0, 2*math.pi); rgba(ctx, RED, 0.35 * pa); ctx.set_line_width(3); ctx.stroke()
        ctx.arc(px, py, 8, 0, 2*math.pi); rgba(ctx, RED, pa); ctx.fill()
        text(ctx, f"{kw(PEAK_U)} kW", px + 34, py + 12, 40, RED, pa, True)
    # final flat level
    fa = A * seg(s, 20.2, 21.2)
    if fa > 0.01:
        yl = Y(PEAK_M)
        text(ctx, f"{kw(PEAK_M)} kW", X(32), yl - 22, 36, GOLD, fa, True, 'r')

    # ---- KPIs
    ky = 1640
    peak_now = P.sum(0).max()
    kcol = lerpc(RED, GOLD, mean_p)
    ka = A * seg(s, 8.8, 9.8)
    if ka > 0.01:
        text(ctx, 'PICO', MX, ky, 24, MUTED, ka, True, spacing=2)
        text(ctx, f"{kw(peak_now)} kW", MX, ky + 74, 68, kcol, ka, True)
        text(ctx, 'ENERGÍA', W/2 + 40, ky, 24, MUTED, ka, True, spacing=2)
        text(ctx, f"{int(round(P.sum()*DT))} kWh", W/2 + 40, ky + 74, 68, TXT, ka, True)
    ra = A * seg(s, T_KPI, T_KPI + 0.8)
    if ra > 0.01:
        red = (PEAK_U - PEAK_M) / PEAK_U * 100
        rrect(ctx, MX, ky + 118, W - 2*MX, 96, 20); rgba(ctx, GOLD, 0.12 * ra); ctx.fill_preserve()
        rgba(ctx, GOLD, 0.8 * ra); ctx.set_line_width(2); ctx.stroke()
        text(ctx, f"−{int(round(red))} % de pico  ·  5/5 al 80 %", W/2, ky + 180 + (1 - ra)*10, 38, GOLD, ra, True, 'c')

    text(ctx, 'Escenario ilustrativo · cargadores de 7,4 kW · baterías de 60 kWh', W/2, 1890, 20, MUTED, 0.8 * A, False, 'c')
    return surf

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'ev_carga_inteligente.mp4'
    if len(sys.argv) > 2:  # stills mode
        for sec in map(float, sys.argv[2:]):
            frame(sec).write_to_png(f'still_{sec:05.1f}.png')
        sys.exit()
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.Popen([ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                          '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for f in range(FR):
        p.stdin.write(bytes(frame(f / FPS).get_data()))
        if f % 150 == 0: print(f, flush=True)
    p.stdin.close(); p.wait(); print('done', out)
