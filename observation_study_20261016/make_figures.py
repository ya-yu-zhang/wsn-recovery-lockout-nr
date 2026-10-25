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
            ax.set_ylim(5.05, -0.55)  # room for open mean diamonds below each cloud
            ax.grid(axis='x', color='#DDDDDD', lw=0.6, zorder=0)
            ax.set_title(f'{panel_ids[row][col]}  {n} nodes', loc='left',
                         fontsize=10, fontweight='bold')
            ax.set_xlabel(
                'Service difference vs Legacy (pp)' if col == 0
                else 'Control DATA reduction vs Legacy (%)'
            )
            if col == 0:
                if n == 10:
                    ax.text(-29.8, 3.55, 'Lockout Zone\n(service ≤ −0.5 pp)',
                            fontsize=7.5, color='#7B241C', va='top', ha='left',
                            linespacing=1.25)
                else:
                    ax.text(-0.80, 3.55, 'Lockout\nZone',
                            fontsize=6.5, color='#7B241C', va='top', ha='left',
                            linespacing=1.15)

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
        Line2D([0], [0], color='black', ls=':', lw=1.2,
               label='Frozen criteria (−0.5 pp / 20%)'),
    ]
    f.legend(handles=handles, loc='lower center', ncol=3, frameon=False,
             bbox_to_anchor=(0.5, -0.015), fontsize=8, columnspacing=1.0,
             handletextpad=0.4)
    f.tight_layout(rect=(0, 0.09, 1, 1))
    save(f, 1)


def _draw_node(ax, xy, label, kind='relay', removed=False):
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
        ax.plot([x - s * 0.45, x + s * 0.45], [y - s * 0.45, y + s * 0.45],
                color='#922B21', lw=2.0, zorder=5)
        ax.plot([x - s * 0.45, x + s * 0.45], [y + s * 0.45, y - s * 0.45],
                color='#922B21', lw=2.0, zorder=5)
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


def fig2(facts):
    assert facts['closing']['gate_blocked'] == 15 and facts['closing']['shadow_known'] == 11
    assert facts['closing']['geometry_available'] == 15
    assert facts['full_v2']['geometry_available'] == 5

    f = plt.figure(figsize=(7.5, 4.7))
    ax_l = f.add_axes([0.035, 0.08, 0.38, 0.84])
    ax_r = f.add_axes([0.46, 0.08, 0.52, 0.84])

    # ----- LEFT: schematic topology -----
    ax_l.set_xlim(0, 6.2)
    ax_l.set_ylim(0, 6.2)
    ax_l.axis('off')
    ax_l.set_title('(a)  Topology after relay removal', loc='left',
                   fontsize=10, fontweight='bold', pad=6)

    pos = {
        0: (1.0, 4.8),
        8: (2.6, 4.8),
        6: (4.0, 4.8),
        9: (5.4, 3.1),
        1: (1.0, 1.4),
        4: (2.6, 1.4),
        5: (4.0, 1.4),
    }
    _draw_link(ax_l, pos[0], pos[8], style='broken')
    _draw_link(ax_l, pos[8], pos[6], style='broken')
    _draw_link(ax_l, pos[6], pos[9], style='broken')
    _draw_link(ax_l, pos[1], pos[4], style='ok')
    _draw_link(ax_l, pos[4], pos[5], style='ok')
    _draw_link(ax_l, pos[5], pos[9], style='ok')

    _draw_node(ax_l, pos[0], '0', kind='source')
    _draw_node(ax_l, pos[1], '1', kind='source')
    _draw_node(ax_l, pos[8], '8', kind='relay')
    _draw_node(ax_l, pos[6], '6', kind='relay', removed=True)
    _draw_node(ax_l, pos[4], '4', kind='relay')
    _draw_node(ax_l, pos[5], '5', kind='relay')
    _draw_node(ax_l, pos[9], '9', kind='gateway')

    ax_l.text(2.6, 5.45, 'Source 0 stuck on v2:  0–8–6–9', fontsize=7.5,
              color='#922B21', ha='center',
              bbox=dict(boxstyle='round,pad=0.25', fc='#FDEDEC', ec='#E6B0AA', lw=0.6))
    ax_l.text(2.6, 0.45, 'Source 1 installed v3:  1–4–5–9', fontsize=7.5,
              color='#196F3D', ha='center',
              bbox=dict(boxstyle='round,pad=0.25', fc='#E8F8F5', ec='#A9DFBF', lw=0.6))
    ax_l.text(5.4, 2.35, 'Gateway', fontsize=7, color='#196F3D', ha='center')

    ax_l.add_patch(FancyBboxPatch((0.15, 2.55), 2.35, 1.35, boxstyle='round,pad=0.05',
                                  facecolor='white', edgecolor='#D0D3D4', lw=0.7, zorder=1))
    ax_l.plot([0.35, 0.85], [3.55, 3.55], color='#922B21', ls='--', lw=1.5)
    ax_l.plot(0.60, 3.55, 'x', color='#922B21', ms=7, mew=1.8)
    ax_l.text(1.0, 3.55, 'Broken path', fontsize=7, va='center', color='#344054')
    ax_l.annotate('', xy=(0.85, 3.15), xytext=(0.35, 3.15),
                  arrowprops=dict(arrowstyle='->', color='#1E8449', lw=1.4))
    ax_l.text(1.0, 3.15, 'Intact path', fontsize=7, va='center', color='#344054')
    ax_l.text(0.35, 2.75, 'Schematic (not physical\ncoordinates)', fontsize=6.5,
              color='#7F8C8D', va='center', linespacing=1.2)

    # ----- RIGHT: timeline -----
    ax_r.set_xlim(215, 325)
    ax_r.set_ylim(0, 10)
    ax_r.axis('off')
    ax_r.set_title('(b)  Decision lockout timeline', loc='left',
                   fontsize=10, fontweight='bold', pad=6)

    y0 = 3.2
    ax_r.annotate('', xy=(320, y0), xytext=(220, y0),
                  arrowprops=dict(arrowstyle='->', lw=1.2, color='#344054'))
    ax_r.text(322, y0, 't (s)', fontsize=8, va='center', color='#344054')

    for t, lab, col in (
        (225, '225\nremoval', '#922B21'),
        (235, '235', '#B9770E'),
        (240, '240', '#B9770E'),
        (245, '245\nexit', '#6C3483'),
        (265, '265\naudit', '#1A5276'),
        (315, '315', '#344054'),
    ):
        ax_r.plot([t, t], [y0 - 0.15, y0 + 0.15], color=col, lw=1.3)
        ax_r.text(t, y0 - 0.55, lab, ha='center', va='top', fontsize=7, color=col,
                  linespacing=1.15)

    ax_r.add_patch(FancyBboxPatch((218, 7.35), 28, 2.15, boxstyle='round,pad=0.08',
                                  facecolor='#FDEDEC', edgecolor='#922B21', lw=0.9))
    ax_r.text(232, 8.4, '225 s  Relay 6 removed\nSource 0 keeps v2 on\nroute 0–8–6–9',
              ha='center', va='center', fontsize=7.2, color='#641E16', linespacing=1.35)

    ax_r.add_patch(FancyBboxPatch((248, 7.35), 32, 2.15, boxstyle='round,pad=0.08',
                                  facecolor='#FEF5E7', edgecolor='#B9770E', lw=0.9))
    ax_r.text(264, 8.4, '235–240 s  Install tries\nSrc0 admitted; MAC ends\nCHANNEL_ACCESS_FAILURE',
              ha='center', va='center', fontsize=7.2, color='#7E5109', linespacing=1.35)

    ax_r.add_patch(FancyBboxPatch((282, 7.35), 34, 2.15, boxstyle='round,pad=0.08',
                                  facecolor='#F5EEF8', edgecolor='#6C3483', lw=0.9))
    ax_r.text(299, 8.4, '245 s  Unconfirmed exit\nSrc0 reports v2;\nSrc1 reports v3',
              ha='center', va='center', fontsize=7.2, color='#4A235A', linespacing=1.35)

    # Lockout band — solid light pink (no alpha)
    ax_r.add_patch(FancyBboxPatch((245, 3.55), 70, 3.35, boxstyle='round,pad=0.06',
                                  facecolor='#F5B7B1', edgecolor='#C0392B',
                                  lw=1.0, linestyle='--'))
    ax_r.text(280, 6.55, '245–315 s  Recovery Lockout  (15 blocked checks)',
              ha='center', va='center', fontsize=8, fontweight='bold', color='#922B21')

    ax_r.add_patch(FancyBboxPatch((248, 5.05), 64, 1.15, boxstyle='round,pad=0.04',
                                  facecolor='white', edgecolor='#1E6B80', lw=0.9))
    ax_r.text(280, 5.62,
              'Horizon / Cohort / Closing:  candidates at 15/15 checks\n'
              'Service predicate = installation_unconfirmed → reject',
              ha='center', va='center', fontsize=7.0, color='#1A5276', linespacing=1.35)

    ax_r.add_patch(FancyBboxPatch((248, 3.8), 64, 1.05, boxstyle='round,pad=0.04',
                                  facecolor='white', edgecolor='#B35A35', lw=0.9))
    ax_r.text(280, 4.32,
              'Full v2:  candidates at only 5/15 checks\n'
              '(5× unconfirmed + 10× missing-source) → reject all 15',
              ha='center', va='center', fontsize=7.0, color='#6E2C00', linespacing=1.35)

    ax_r.add_patch(FancyBboxPatch((252, 0.35), 56, 2.35, boxstyle='round,pad=0.06',
                                  facecolor='#EBF5FB', edgecolor='#1A5276', lw=1.0,
                                  linestyle='--'))
    ax_r.plot([265, 265], [y0, 2.7], color='#1A5276', ls=':', lw=0.9)
    ax_r.text(280, 1.5,
              '265 s  Offline received-only audit (not executed)\n'
              'offered [36, 60], timely [0, 59]  ·  deficit at 11/15 checks\n'
              'No recovery action taken',
              ha='center', va='center', fontsize=7.0, color='#1A5276', linespacing=1.35)

    save(f, 2)


def main():
    r = json.loads((ROOT / 'results/reanalysis.json').read_text())
    facts = json.loads((ROOT / 'results/recovery_mechanism_findings.json').read_text())
    fig1(r)
    fig2(facts)
    print('Created Fig1 and Fig2 (PNG+EPS) with Lockout Zone and topology+timeline')


if __name__ == '__main__':
    main()
