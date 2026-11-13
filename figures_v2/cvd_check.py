"""Greyscale and colour-vision-deficiency check (Machado et al. 2009, severity 1.0) of the rendered figures.
Writes simulated previews to cvd_check/ and reports the minimum CIE-L* separation between arm colours."""
import numpy as np, matplotlib.image as mpimg, json
from pathlib import Path
M = {'deuteranopia': np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
     'protanopia': np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
     'tritanopia': np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]])}
lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
gam = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, 1) ** (1 / 2.4) - 0.055)
def sim(rgb, m): return np.clip(gam(np.clip(lin(rgb) @ m.T, 0, 1)), 0, 1)
def Lstar(rgb):
    Y = lin(rgb) @ np.array([0.2126, 0.7152, 0.0722]); return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)
out = Path(__file__).parent / 'cvd_check'; out.mkdir(exist_ok=True)
for f in sorted(Path(__file__).parent.glob('Fig*.png')):
    im = mpimg.imread(f)[..., :3].astype(float)[::4, ::4]
    mpimg.imsave(out / f'{f.stem}_grey.png', np.repeat((Lstar(im) / 100)[..., None], 3, axis=2))
    for k, m in M.items(): mpimg.imsave(out / f'{f.stem}_{k}.png', sim(im, m))
arms = {'joint': '#D55E00', 'post_exit': '#0072B2', 'sham': '#999999', 'wait_extend': '#E69F00', 'thresh_relax': '#009E73'}
h = lambda x: np.array([int(x[i:i + 2], 16) / 255 for i in (1, 3, 5)])
rep = {}
for k in ['none'] + list(M):
    L = {a: float(Lstar(h(c) if k == 'none' else sim(h(c)[None], M[k])[0])) for a, c in arms.items()}
    rep[k] = dict(L_star=L, joint_vs_postexit_dL=abs(L['joint'] - L['post_exit']))
Path(out / 'cvd_report.json').write_text(json.dumps(rep, indent=1)); print(json.dumps({k: round(v['joint_vs_postexit_dL'], 1) for k, v in rep.items()}))
