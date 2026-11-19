"""Shared figure style for the SIMPAT submission (Elsevier artwork guidance, fetched 2026-11-11):
vector PDF/EPS with embedded fonts; Arial-metric sans font (Liberation Sans); lettering >= 7 pt at final
size; final width 140 mm (Elsevier 1.5-column size, equal to the elsarticle preprint text width, so the review
PDF shows the true printed size); Okabe-Ito colour-blind-safe palette; no figure frames; panel labels (a), (b)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
MM = 1 / 25.4
W140 = 140 * MM            # 1.5-column width (Elsevier sizing table)
W90 = 90 * MM              # single column
OI = dict(orange='#E69F00', sky='#56B4E9', green='#009E73', yellow='#F0E442', blue='#0072B2',
          vermillion='#D55E00', purple='#CC79A7', black='#000000', grey='#7F7F7F', lightgrey='#E5E5E5')
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Liberation Sans', 'Arial', 'Helvetica'],
    'mathtext.fontset': 'custom', 'mathtext.rm': 'Liberation Sans', 'mathtext.it': 'Liberation Sans:italic',
    'mathtext.bf': 'Liberation Sans:bold',
    'font.size': 7.5, 'axes.titlesize': 7.5, 'axes.labelsize': 7.5, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'legend.fontsize': 7, 'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'lines.linewidth': 0.9, 'axes.spines.top': False,
    'axes.spines.right': False, 'legend.frameon': False, 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'savefig.dpi': 600, 'figure.dpi': 150, 'axes.titleweight': 'normal', 'axes.titlelocation': 'left'})
MIN_PT = 7.0   # all lettering 7-9 pt at final size (Elsevier minimum 7 pt; 6 pt only for sub/superscripts)
ARM = dict(joint='#D55E00', post_exit='#0072B2', sham='#999999', wait_extend='#E69F00', thresh_relax='#009E73')
def panel(ax, letter, x=-0.02, y=1.02, ha='right'):
    ax.text(x, y, f'({letter})', transform=ax.transAxes, fontsize=9, fontweight='bold', ha=ha, va='bottom')
def check_fonts(fig, name, minimum=MIN_PT):
    """Assert every text artist is at least `minimum` pt (6 pt allowed only for sub/superscript-free tick labels is not used)."""
    small = []
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_text().strip() and t.get_visible() and t.get_fontsize() < minimum - 1e-6:
            small.append((t.get_text()[:30], t.get_fontsize()))
    assert not small, (name, small)
def save(fig, out, name):
    check_fonts(fig, name)
    fig.savefig(out / f'{name}.pdf')
    fig.savefig(out / f'{name}.eps')
    fig.savefig(out / f'{name}.png', dpi=600)
    plt.close(fig)
