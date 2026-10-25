"""Scientific figures from all 40 completed cases; Lockout Zone + topology/timeline composite."""
from pathlib import Path
import json, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Circle, Patch, Rectangle

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'figures'
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 9,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'savefig.dpi': 600,
    'ps.fonttype': 42,
    'pdf.fonttype': 42,
})

COLORS = {'multi_failure': '#1E6B80', 'overload': '#B35A35'}
MARKERS = {'multi_failure': 'o', 'overload': 's'}
SEEDS = (2026101511, 2026101512)


def save(fig, n):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f'Fig{n}.png', dpi=600, bbox_inches='tight', facecolor='white')
    # EPS: avoid alpha by redrawing solid light fills already; still may warn on legend Patch
    fig.savefig(OUT / f'Fig{n}.eps', bbox_inches='tight', facecolor='white')
    plt.close(fig)


def _marker_style(scenario, seed):
    filled = seed == SEEDS[0]
    m = MARKERS[scenario]
    c = COLORS[scenario]
    if filled:
        return dict(marker=m, color=c, markerfacecolor=c, markeredgecolor=c,
                    markeredgewidth=0.8, linestyle='None', markersize=5.5)
    return dict(marker=m, color=c, markerfacecolor='white', markeredgecolor=c,
                markeredgewidth=1.15, linestyle='None', markersize=5.5)


def fig1(r):
    models = ['full_v2', 'horizon', 'cohort', 'closing']
    labels = ['Full v2', 'Horizon', 'Cohort', 'Closing']
    panel_ids = [['(a)', '(b)'], ['(c)', '(d)']]
    f, axes = plt.subplots(2, 2, figsize=(7.4, 6.0))

    order = [
        ('multi_failure', 2026101511),
        ('multi_failure', 2026101512),
        ('overload', 2026101511),
        ('overload', 2026101512),
    ]
    # Compact cloud around row center; mean sits clearly below cloud
    offsets = [-0.18, -0.06, 0.06, 0.18]
    mean_dy = 0.72  # below cloud; rows spaced 1.45 apart

    for row, n in enumerate((10, 20)):
        for col, field in enumerate(('service_vs_legacy_pp', 'control_reduction_vs_legacy_percent')):
            ax = axes[row, col]
            if col == 0:
                xlim = (-30.5, 3) if n == 10 else (-0.85, 3.2)
                ax.set_xlim(xlim)
                # Solid light fill (no alpha) for Lockout Zone: service ≤ −0.5 pp
                ax.axvspan(xlim[0], -0.5, color='#F5B7B1', zorder=0)
                ax.axvline(-0.5, color='black', ls=':', lw=1.0, zorder=1)
            else:
                xlim = (8, 38) if n == 10 else (18, 40)
                ax.set_xlim(xlim)
                ax.axvspan(xlim[0], 20, color='#D5D8DC', zorder=0)
                ax.axvline(20, color='black', ls=':', lw=1.0, zorder=1)

            y_pos = [0.0, 1.45, 2.90, 4.35]
            for yi, m in enumerate(models):
                y = y_pos[yi]
                pp = [x for x in r['paired_results'] if x['nodes'] == n and x['model'] == m]
                for p in pp:
                    k = order.index((p['scenario'], p['seed']))
                    ax.plot(p[field], y + offsets[k], zorder=3, **_marker_style(p['scenario'], p['seed']))
                mean_v = statistics.mean(p[field] for p in pp)
                # Mean on a dedicated track below the cloud (never covers matched-cell markers)
                ax.plot([mean_v, mean_v], [y + 0.22, y + mean_dy - 0.04],
                        color='#444444', lw=0.55, zorder=2)
                ax.plot(mean_v, y + mean_dy, marker='D', color='black',
                        markerfacecolor='white', markeredgecolor='black',
                        markeredgewidth=1.25, markersize=5.4, zorder=5,
                        linestyle='None')

            ax.set_yticks(y_pos, labels)
            ax.set_ylim(5.40, -0.55)  # room for the last row's mean diamond (y = 5.07)
            ax.grid(axis='x', color='#DDDDDD', lw=0.6, zorder=0)
            ax.set_title(f'{panel_ids[row][col]}  {n} nodes', loc='left',
                         fontsize=10, fontweight='bold')
            ax.set_xlabel(
                'Service difference vs Legacy (pp)' if col == 0
                else 'Control DATA reduction vs Legacy (%)'
            )
            if col == 0:
                if n == 10:
                    # empty band between the -27.69 cell column and the mean diamonds
                    ax.text(-25.6, 2.18, 'Lockout Zone\n(service ≤ −0.5 pp)',
                            fontsize=7.5, color='#7B241C', va='center', ha='left',
                            linespacing=1.25)
                else:
                    # narrow band: vertical label kept inside the shaded region
                    ax.text(-0.675, 2.18, 'Lockout Zone', rotation=90,
                            fontsize=6.5, color='#7B241C', va='center', ha='center')
            else:
                ax.text(xlim[0] + (20 - xlim[0]) / 2, 2.18, 'DATA < 20%', rotation=90,
                        fontsize=6.5, color='#4D5656', va='center', ha='center')

    handles = [
        Line2D([0], [0], marker='o', ls='', color=COLORS['multi_failure'],
               markerfacecolor=COLORS['multi_failure'], markersize=6,
               label='Relay removals (seed A, filled)'),
        Line2D([0], [0], marker='o', ls='', color=COLORS['multi_failure'],
               markerfacecolor='white', markeredgecolor=COLORS['multi_failure'],
               markeredgewidth=1.1, markersize=6,
               label='Relay removals (seed B, open)'),
        Line2D([0], [0], marker='s', ls='', color=COLORS['overload'],
               markerfacecolor=COLORS['overload'], markersize=6,
               label='Overload (seed A, filled)'),
        Line2D([0], [0], marker='s', ls='', color=COLORS['overload'],
               markerfacecolor='white', markeredgecolor=COLORS['overload'],
               markeredgewidth=1.1, markersize=6,
               label='Overload (seed B, open)'),
        Line2D([0], [0], marker='D', ls='', color='black', markerfacecolor='white',
               markeredgecolor='black', markeredgewidth=1.2, markersize=5.5,
               label='Four-cell mean'),
        Patch(facecolor='#F5B7B1', edgecolor='none',
              label='Lockout Zone (service ≤ −0.5 pp)'),
        Patch(facecolor='#D5D8DC', edgecolor='none',
              label='DATA reduction < 20%'),
        Line2D([0], [0], color='black', ls=':', lw=1.2,
               label='Frozen criteria (−0.5 pp / 20%)'),
    ]
    leg = f.legend(handles=handles, loc='lower center', ncol=4, frameon=False,
                   bbox_to_anchor=(0.5, -0.015), fontsize=7.6, columnspacing=1.0,
                   handletextpad=0.4)
    f.tight_layout(rect=(0, 0.075, 1, 1))
    _check_fig1(f, axes, leg)
    save(f, 1)


def _check_fig1(f, axes, leg):
    """Fail the build if any annotation overlaps a data marker or leaves its panel,
    or if the legend collides with the axes."""
    f.canvas.draw()
    rend = f.canvas.get_renderer()
    bad = []
    for ax in axes.flat:
        axb = ax.get_window_extent(rend)
        pts = []
        for line in ax.get_lines():
            if line.get_marker() in ('None', None, '') or line.get_linestyle() not in ('None', ''):
                continue
            pts += list(ax.transData.transform(line.get_xydata()))
        for t in ax.texts:
            tb = t.get_window_extent(rend).expanded(1.0, 1.0)
            if not (axb.x0 <= tb.x0 and tb.x1 <= axb.x1 and axb.y0 <= tb.y0 and tb.y1 <= axb.y1):
                bad.append('outside panel: ' + t.get_text()[:20])
            for x, y in pts:
                if tb.x0 - 4 <= x <= tb.x1 + 4 and tb.y0 - 4 <= y <= tb.y1 + 4:
                    bad.append('marker under label: ' + t.get_text()[:20])
                    break
        # zone labels must sit inside their shaded band
        for t in ax.texts:
            tb = t.get_window_extent(rend)
            x0, x1 = ax.get_xlim()
            edge = -0.5 if 'Lockout' in t.get_text() else 20
            xe = ax.transData.transform((edge, 0))[0]
            xs = ax.transData.transform((x0, 0))[0]
            if not (xs <= tb.x0 and tb.x1 <= xe):
                bad.append('label outside zone: ' + t.get_text()[:20])
    for ax in axes.flat:
        (x0, x1), (y1, y0) = ax.get_xlim(), ax.get_ylim()
        for line in ax.get_lines():
            for x, y in line.get_xydata():
                if line.get_marker() not in ('None', None, '') and not (x0 <= x <= x1 and min(y0, y1) + 0.12 <= y <= max(y0, y1) - 0.12):
                    bad.append(f'marker clipped at ({x:.2f}, {y:.2f})')
    lb = leg.get_window_extent(rend)
    for ax in axes.flat:
        if ax.get_tightbbox(rend).overlaps(lb):
            bad.append('legend overlaps axes')
    assert not bad, bad
    print('Fig1 layout checks passed')


def _draw_node(ax, xy, label, kind='relay', removed=False, note=True):
    x, y = xy
    if kind == 'source':
        face, edge, r = '#D6EAF8', '#1A5276', 0.38
    elif kind == 'gateway':
        face, edge, r = '#D5F5E3', '#196F3D', 0.42
    else:
        face, edge, r = '#F4F6F7', '#344054', 0.34
    if removed:
        face, edge = '#FADBD8', '#922B21'
    ax.add_patch(Circle((x, y), r, facecolor=face, edgecolor=edge, lw=1.3, zorder=3))
    ax.text(x, y, label, ha='center', va='center', fontsize=9, fontweight='bold',
            color=edge, zorder=4)
    if removed:
        s = 0.55
        for sg in (1, -1):
            ax.plot([x - s * 0.5, x + s * 0.5], [y - sg * s * 0.5, y + sg * s * 0.5],
                    color='#D98880', lw=1.2, zorder=3.5)
    if removed and note:
        ax.text(x, y - 0.72, 'removed\nat 225 s', ha='center', va='top',
                fontsize=7, color='#922B21')


def _draw_link(ax, a, b, style='ok'):
    xa, ya = a
    xb, yb = b
    if style == 'ok':
        ax.annotate('', xy=(xb, yb), xytext=(xa, ya),
                    arrowprops=dict(arrowstyle='->', lw=1.6, color='#1E8449',
                                    shrinkA=12, shrinkB=12), zorder=2)
    else:
        ax.annotate('', xy=(xb, yb), xytext=(xa, ya),
                    arrowprops=dict(arrowstyle='->', lw=1.6, color='#922B21',
                                    linestyle='dashed', shrinkA=12, shrinkB=12),
                    zorder=2)
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        ax.plot(mx, my, marker='x', markersize=10, color='#922B21',
                markeredgewidth=2.2, zorder=5)


_FIT_CHECKS = []   # (text_artist, patch_artist, label) pairs verified after drawing


def _card(ax, x0, y0, w, h, lines, fc, ec, tc, fs=7.2, bold_first=True,
          ls='-', lw=0.9, rs=1.2, lsp=1.35, zorder=3):
    """Card sized in layout units (NOT time units); text centred with padding."""
    p = FancyBboxPatch((x0, y0), w, h, boxstyle=f'round,pad=0,rounding_size={rs}',
                       facecolor=fc, edgecolor=ec, lw=lw, linestyle=ls, zorder=zorder)
    ax.add_patch(p)
    cx, cy = x0 + w / 2, y0 + h / 2
    if bold_first and len(lines) > 1:
        # title line + body, stacked around the centre
        n = len(lines)
        step = fs * lsp / 72.0 / ax._unit_in      # one text line in layout units
        top = cy + step * (n - 1) / 2
        arts = []
        for i, s in enumerate(lines):
            arts.append(ax.text(cx, top - i * step, s, ha='center', va='center',
                                fontsize=fs, color=tc, zorder=zorder + 1,
                                fontweight='bold' if i == 0 else 'normal'))
    else:
        arts = [ax.text(cx, cy, '\n'.join(lines), ha='center', va='center', fontsize=fs,
                        color=tc, linespacing=lsp, zorder=zorder + 1)]
    for a in arts:
        _FIT_CHECKS.append((a, p, lines[0]))
    return p


def fig2(facts, partial=None):
    assert facts['closing']['gate_blocked'] == 15 and facts['closing']['shadow_known'] == 11
    assert facts['closing']['geometry_available'] == 15
    assert facts['full_v2']['geometry_available'] == 5
    assert facts['full_v2']['service_reasons'] == {'installation_unconfirmed': 5, 'missing_fresh_source': 10}
    assert facts['closing']['first_shadow']['offered'] == [36, 60] and facts['closing']['first_shadow']['timely'] == [0, 59]
    if partial is not None:   # Horizon/Cohort/Closing counts quoted in panel (b)
        for m in ('horizon', 'cohort', 'closing'):
            assert partial[m]['checks'] == 15 and partial[m]['geometry_available'] == 15
            assert partial[m]['service_reasons'] == {'installation_unconfirmed': 15}
            assert partial[m]['shadow_deficit'] == 11
    _FIT_CHECKS.clear()

    FW, FH = 7.5, 4.75
    f = plt.figure(figsize=(FW, FH))
    # Panel geometry in figure fractions
    la = [0.005, 0.06, 0.345, 0.80]
    ra = [0.375, 0.02, 0.62, 0.885]
    ax_l = f.add_axes(la)
    ax_r = f.add_axes(ra)
    f.text(0.012, 0.965, '(a)  Topology after relay removal', fontsize=10,
           fontweight='bold', ha='left', va='center')
    f.text(0.382, 0.965, '(b)  Decision lockout timeline', fontsize=10,
           fontweight='bold', ha='left', va='center')

    # ----- LEFT: schematic topology (equal aspect -> round nodes) -----
    wl, hl = la[2] * FW, la[3] * FH
    ax_l.set_xlim(0, 6.2)
    ax_l.set_ylim(3.1 - 6.2 * hl / wl / 2, 3.1 + 6.2 * hl / wl / 2)
    ax_l.set_aspect('equal', adjustable='box')
    ax_l.axis('off')

    pos = {0: (0.75, 4.8), 8: (2.35, 4.8), 6: (3.95, 4.8), 9: (5.45, 3.1),
           1: (0.75, 1.4), 4: (2.35, 1.4), 5: (3.95, 1.4)}
    _draw_link(ax_l, pos[0], pos[8], style='broken')
    _draw_link(ax_l, pos[8], pos[6], style='broken')
    _draw_link(ax_l, pos[6], pos[9], style='broken')
    _draw_link(ax_l, pos[1], pos[4], style='ok')
    _draw_link(ax_l, pos[4], pos[5], style='ok')
    _draw_link(ax_l, pos[5], pos[9], style='ok')
    for n, k in ((0, 'source'), (1, 'source'), (8, 'relay'), (4, 'relay'),
                 (5, 'relay'), (9, 'gateway')):
        _draw_node(ax_l, pos[n], str(n), kind=k)
    _draw_node(ax_l, pos[6], '6', kind='relay', removed=True, note=False)
    ax_l.text(3.95, 5.42, 'removed at 225 s', ha='center', va='bottom',
              fontsize=7, color='#922B21')

    ax_l.text(2.35, 6.25, 'Source 0 stuck on v2:  0–8–6–9', fontsize=7.5,
              color='#922B21', ha='center', va='center',
              bbox=dict(boxstyle='round,pad=0.3', fc='#FDEDEC', ec='#E6B0AA', lw=0.6))
    ax_l.text(2.35, 0.45, 'Source 1 installed v3:  1–4–5–9', fontsize=7.5,
              color='#196F3D', ha='center', va='center',
              bbox=dict(boxstyle='round,pad=0.3', fc='#E8F8F5', ec='#A9DFBF', lw=0.6))
    ax_l.text(5.68, 2.55, 'Gateway', fontsize=7, color='#196F3D', ha='center', va='top')

    # legend box
    lg = FancyBboxPatch((0.15, 2.35), 3.2, 1.6, boxstyle='round,pad=0,rounding_size=0.12',
                        facecolor='white', edgecolor='#B3B6B7', lw=0.7, zorder=1)
    ax_l.add_patch(lg)
    ax_l.plot([0.35, 0.85], [3.65, 3.65], color='#922B21', ls='--', lw=1.5, zorder=2)
    ax_l.plot(0.60, 3.65, 'x', color='#922B21', ms=7, mew=1.8, zorder=2)
    t1 = ax_l.text(1.0, 3.65, 'Broken path', fontsize=7, va='center', color='#344054')
    ax_l.annotate('', xy=(0.85, 3.25), xytext=(0.35, 3.25),
                  arrowprops=dict(arrowstyle='->', color='#1E8449', lw=1.4))
    t2 = ax_l.text(1.0, 3.25, 'Intact path', fontsize=7, va='center', color='#344054')
    t3 = ax_l.text(0.35, 2.72, 'Schematic (not physical\ncoordinates)', fontsize=6.5,
                   color='#5D6D7E', va='center', linespacing=1.2)
    for t in (t1, t2, t3):
        _FIT_CHECKS.append((t, lg, 'legend'))

    # ----- RIGHT: layout units, x 0..100, equal aspect -----
    wr, hr = ra[2] * FW, ra[3] * FH
    ax_r._unit_in = wr / 100.0
    H = 100.0 * hr / wr
    ax_r.set_xlim(0, 100)
    ax_r.set_ylim(0, H)
    ax_r.axis('off')

    T0, T1, X0, X1 = 220.0, 320.0, 3.0, 92.0
    tx = lambda t: X0 + (t - T0) * (X1 - X0) / (T1 - T0)

    # Row 1: three equal-width event cards (independent of the time scale)
    cw, ch, gap = 31.0, 15.0, 3.0
    ytop = H - 1.5
    cy0 = ytop - ch
    cards = [
        (225, ['225 s  Relay 6 removed', 'Source 0 keeps v2', 'on route 0–8–6–9'],
         '#FDEDEC', '#922B21', '#641E16'),
        ((235, 240), ['235–240 s  Install tries', 'Src0 admitted; MAC ends',
                      'CHANNEL_ACCESS_FAILURE'],
         '#FEF5E7', '#B9770E', '#7E5109'),
        (245, ['245 s  Unconfirmed exit', 'Src0 reports v2', 'Src1 reports v3'],
         '#F5EEF8', '#6C3483', '#4A235A'),
    ]
    y_axis = cy0 - 14.0
    for i, (t, lines, fc, ec, tc) in enumerate(cards):
        x0 = 1.0 + i * (cw + gap)
        _card(ax_r, x0, cy0, cw, ch, lines, fc, ec, tc, fs=7.0)
        # leader: card bottom-centre -> elbow -> event time on the axis
        xc = x0 + cw / 2
        if isinstance(t, tuple):
            xa, xb = tx(t[0]), tx(t[1])
            xt = (xa + xb) / 2
            ax_r.plot([xa, xa, xb, xb], [y_axis + 1.0, y_axis + 2.0, y_axis + 2.0, y_axis + 1.0],
                      color=ec, lw=1.0, zorder=4)
            yend = y_axis + 2.0
        else:
            xt = tx(t)
            yend = y_axis + 1.0
        ymid = y_axis + {225: 8.0, (235, 240): 8.0, 245: 4.5}[t]
        ax_r.plot([xc, xc, xt, xt], [cy0, ymid, ymid, yend], color=ec, lw=0.9, zorder=2)
        ax_r.plot(xt, yend, marker='o', ms=3.0, color=ec, zorder=5)

    # Timeline axis with lockout span drawn on it
    ax_r.add_patch(Rectangle((tx(245), y_axis - 1.0), tx(315) - tx(245), 2.0,
                             facecolor='#F5B7B1', edgecolor='#C0392B', lw=0.8, zorder=1))
    ax_r.annotate('', xy=(X1 + 2.5, y_axis), xytext=(X0 - 1.0, y_axis),
                  arrowprops=dict(arrowstyle='->', lw=1.2, color='#344054'), zorder=3)
    ax_r.text(X1 + 3.2, y_axis, 't (s)', fontsize=7.5, va='center', ha='left', color='#344054')
    tick_arts = []
    for t, lab, col in ((225, '225\nremoval', '#922B21'), (235, None, '#B9770E'),
                        (240, None, '#B9770E'), (245, '245\nexit', '#6C3483'),
                        (265, '265\naudit', '#1A5276'), (315, '315\nend', '#344054')):
        ax_r.plot([tx(t)] * 2, [y_axis - 1.4, y_axis + 1.0], color=col, lw=1.3, zorder=4)
        if lab:
            tick_arts.append(ax_r.text(tx(t), y_axis - 2.2, lab, ha='center', va='top',
                                       fontsize=6.8, color=col, linespacing=1.1))
    # 235 and 240 are 5 s apart: one combined label on a lower row, joined to both ticks
    xm = (tx(235) + tx(240)) / 2
    ax_r.plot([tx(235), tx(235), tx(240), tx(240)],
              [y_axis - 1.4, y_axis - 2.4, y_axis - 2.4, y_axis - 1.4], color='#B9770E', lw=0.8, zorder=4)
    ax_r.plot([xm, xm], [y_axis - 2.4, y_axis - 6.4], color='#B9770E', lw=0.6, ls=':', zorder=4)
    low = ax_r.text(xm, y_axis - 6.6, '235/240', ha='center', va='top',
                    fontsize=6.8, color='#B9770E', linespacing=1.1)
    ax_r.plot(tx(265), y_axis, marker='D', ms=4.0, color='#1A5276', zorder=6)

    # Lockout panel (full width, solid fill), two white inner cards with padding
    lk_top = y_axis - 11.0
    lk_h = 28.5
    lk_y0 = lk_top - lk_h
    lk = FancyBboxPatch((1.0, lk_y0), 97.0, lk_h, boxstyle='round,pad=0,rounding_size=1.5',
                        facecolor='#F9D5D1', edgecolor='#C0392B', lw=1.0, linestyle='--',
                        zorder=1)
    ax_r.add_patch(lk)
    ttl = ax_r.text(49.5, lk_top - 3.2, '245–315 s  Recovery Lockout (15 blocked checks)',
                    ha='center', va='center', fontsize=7.8, fontweight='bold', color='#922B21')
    _FIT_CHECKS.append((ttl, lk, 'lockout title'))
    _card(ax_r, 4.0, lk_y0 + 13.0, 91.0, 9.2,
          ['Horizon / Cohort / Closing: candidates at 15/15 checks',
           'Service predicate = installation_unconfirmed → reject'],
          'white', '#1E6B80', '#1A5276', fs=7.0, zorder=2)
    _card(ax_r, 4.0, lk_y0 + 2.2, 91.0, 9.2,
          ['Full v2: candidates at only 5/15 checks',
           '5 unconfirmed + 10 missing-source → reject all 15'],
          'white', '#B35A35', '#6E2C00', fs=7.0, zorder=2)

    # Audit card (separate, below the lockout, keyed to the ◆ 265 marker)
    au_h = lk_y0 - 3.0 - 1.0
    _card(ax_r, 1.0, 1.0, 97.0, au_h,
          ['◆ 265 s  Offline received-only audit (not executed)',
           'offered [36, 60], timely [0, 59]; deficit at 11/15 checks',
           'No recovery action taken'],
          '#EBF5FB', '#1A5276', '#1A5276', fs=7.0, ls='--', lw=1.0)

    # ---- automatic layout verification ----
    f.canvas.draw()
    rend = f.canvas.get_renderer()
    bad = []
    for t, p, name in _FIT_CHECKS:
        tb = t.get_window_extent(rend)
        pb = p.get_window_extent(rend)
        m = 2.0  # px padding required at 100 dpi
        if not (tb.x0 >= pb.x0 + m and tb.x1 <= pb.x1 - m and
                tb.y0 >= pb.y0 + m and tb.y1 <= pb.y1 - m):
            bad.append(name)
    ext = [a.get_window_extent(rend) for a in tick_arts]
    for i in range(len(ext) - 1):
        if ext[i].x1 + 3 > ext[i + 1].x0:
            bad.append(f'tick overlap {i}')
    lowb = low.get_window_extent(rend)
    for e in ext:   # combined lower label must not collide with first-row labels
        if e.overlaps(lowb):
            bad.append('lower tick label overlap')
    ext = ext + [lowb]
    if ext and min(e.y0 for e in ext) <= lk.get_window_extent(rend).y1 + 2:
        bad.append('ticks hit lockout')
    for ax in (ax_l, ax_r):
        axb = ax.get_window_extent(rend)
        for t in ax.texts:
            tb = t.get_window_extent(rend)
            if tb.width and (tb.x0 < axb.x0 - 1 or tb.x1 > axb.x1 + 1 or
                             tb.y0 < axb.y0 - 1 or tb.y1 > axb.y1 + 1):
                bad.append('outside axes: ' + t.get_text()[:25])
    assert not bad, bad
    print('Fig2 layout checks passed:', len(_FIT_CHECKS), 'text/box pairs')

    save(f, 2)


def main():
    r = json.loads((ROOT / 'results/reanalysis.json').read_text())
    facts = json.loads((ROOT / 'results/recovery_mechanism_findings.json').read_text())
    fig1(r)
    pfile = ROOT / 'results/partial_installation_summary.json'
    fig2(facts, json.loads(pfile.read_text()) if pfile.exists() else None)
    print('Created Fig1 and Fig2 (PNG+EPS) with Lockout Zone and topology+timeline')


if __name__ == '__main__':
    main()
