"""Read-only cross-check: every Phase-2/3 number in manuscript.tex or supplementary.tex is recomputed from the
result JSON files under phase2_study_20261111/ and must appear in the main or supplementary text
(expert revision 2026-11-11: numbers moved to the supplement are checked there; new M1-M10 wording is checked).
Runs no simulation and writes check_phase23_numbers.json / .txt next to this script."""
import json, hashlib, math, re, sys
from pathlib import Path
import os
HERE=Path(__file__).resolve().parent
P2=Path(__file__).resolve().parents[1]
R=P2/'results'
# The manuscript LaTeX and the unredacted registration files are not part of the
# public data deposit. Authors (or editor/reviewers with those files) set
# SIMPAT_TEX_DIR to a folder that contains manuscript.tex and supplementary.tex
# and place the unredacted registrations beside the redacted copies.
tex_dir=Path(os.environ['SIMPAT_TEX_DIR']) if os.environ.get('SIMPAT_TEX_DIR') else HERE
if not (tex_dir/'manuscript.tex').is_file() or not (tex_dir/'supplementary.tex').is_file():
    sys.stderr.write(
        "check_phase23_numbers.py compares V&V numbers to the manuscript LaTeX.\n"
        "Those source files, and the unredacted Phase-2/2b registrations, are not\n"
        "in the public data repository. Set SIMPAT_TEX_DIR to a directory that\n"
        "contains manuscript.tex and supplementary.tex, and provide the unredacted\n"
        "registration files, then rerun. The zero-friction public check is\n"
        "public_release_amp_repro_20261104/scripts/print_paper_endpoints.py.\n"
    )
    sys.exit(2)
main_tex=(tex_dir/'manuscript.tex').read_text(); supp_tex=(tex_dir/'supplementary.tex').read_text()
tex=main_tex+'\n'+supp_tex
flat=re.sub(r'\s+',' ',tex); flat_main=re.sub(r'\s+',' ',main_tex); flat_supp=re.sub(r'\s+',' ',supp_tex)
J=lambda p: json.loads((P2/p).read_text())
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[]; fails=[]
def need(label, value, *snippets):
    """value: recomputed from source; snippets: strings (built from value) that must occur in the text."""
    ok=all(sn in flat for sn in snippets)
    checks.append({'label':label,'value':value,'snippets':list(snippets),'ok':ok})
    if not ok: fails.append(label)
def f3(x): return f'{x:.3f}'
def f2(x): return f'{x:.2f}'
def thou(n): return f'{n:,}'
def wilson(k,n,z=1.959963984540054):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h), min(1,c+h)
def ci(k,n): lo,hi=wilson(k,n); return f'{lo:.2f}--{hi:.2f}'

# ---------------- registrations and hashes
need('Phase-2 registration SHA', sha(P2/'REGISTRATION_PHASE2_20261111.json'), sha(P2/'REGISTRATION_PHASE2_20261111.json'))
need('Addendum 1 SHA', sha(P2/'ADDENDUM_PHASE2_20261111b.md'), sha(P2/'ADDENDUM_PHASE2_20261111b.md'))
need('Phase-2b registration SHA', sha(P2/'REGISTRATION_PHASE2B_20261111.json'), sha(P2/'REGISTRATION_PHASE2B_20261111.json'))
reg=J('REGISTRATION_PHASE2_20261111.json')
tb=sha(P2/'flocklab/wsn-closed-loop-trace')
need('trace binary SHA (file)', tb, tb)
need('trace binary SHA (registration)', reg['trace_binary_sha256'], reg['trace_binary_sha256'])
cal=sha(P2/'mirror/calibration.json'); need('calibration SHA prefix/suffix', cal, cal[:8]+r'\ldots'+cal[-4:])
doe_design=P2/'doe/design.json'
if doe_design.exists():
    d=sha(doe_design); need('DOE design SHA prefix/suffix', d, d[:8]+r'\ldots '+d[-5:])
need('SimPy version', reg['simpy_version'], 'SimPy~'+reg['simpy_version'].split()[0])
FROZEN='1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24'
need('frozen registration referenced', FROZEN, FROZEN, '1f37be33\\ldots6a24')

# ---------------- Mode C
cp=J('results/dock_C_probe.json')['summary']; cf=J('results/dock_C_full.json')['summary']
for nm,d in [('probe',cp),('full',cf)]:
    assert d['pass'] and all(d[k]==1.0 for k in ['C1','C2','C3','C4'])
need('Mode C probe n', cp['n'], f"Mode C probe & {cp['n']} & C1--C4 $=$ 1.000 & Pass")
need('Mode C full n', cf['n'], f"Mode C full & {cf['n']} & C1--C4 $=$ 1.000 & Pass", f"registered full set of {cf['n']} cases")
ext=J('results/dock_C_extended.json')['summary']; inc=J('results/dock_C_extended_incl_late.json')['summary']
sets=[k for k,v in ext.items() if isinstance(v,dict) and 'n' in v]
n=sum(ext[k]['n'] for k in sets); c1=sum(ext[k]['C1'] for k in sets); c2=sum(ext[k]['C2'] for k in sets)
pa=sum(ext[k]['phi_agree'] for k in sets); pe=sum(ext[k]['phi_eval'] for k in sets)
ra=sum(ext[k]['reason_agree'] for k in sets); rt=sum(ext[k]['ticks'] for k in sets)
c2i=sum(inc[k]['C2'] for k in sets)
assert c1==n and pa==pe and ra==rt and c2i==n
need('Mode C extension sets', len(sets), 'all nine frozen case sets' if len(sets)==9 else 'MISMATCH')
need('Mode C extension cases (main)', n, f'An exploratory extension to {thou(n)} cases from all nine frozen case sets')
need('Mode C extension total row (S-table)', [n,c1,c2,c2i,pa,pe,ra,rt], f'Total & {thou(n)} & {thou(c1)} & {thou(c2)} & {thou(c2i)} & {thou(pa)}/{thou(pe)} & {thou(ra)}/{thou(rt)}')
for k in sets:
    v=ext[k]; vi=inc[k]
    need(f'Mode C extension row {k}', v, '\\texttt{'+k.replace('_','\\_')+'}'+f" & {thou(v['n'])} & {thou(v['C1'])} & {thou(v['C2'])} & {thou(vi['C2'])} & {thou(v['phi_agree'])}/{thou(v['phi_eval'])} & {thou(v['reason_agree'])}/{thou(v['ticks'])}")
need('Mode C strict C2 misses', n-c2, f'All {n-c2} strict-C2 misses are wait exits that a later confirmation rescued')
skipped=ext.get('skipped', None)
if isinstance(skipped,(int,list,dict)):
    sk=skipped if isinstance(skipped,int) else len(skipped)
    need('Mode C skipped', sk, f'{sk} cases of arms the mirror does not implement were skipped')
else:
    need('Mode C skipped (changelog)', 465, '465 cases of arms the mirror does not implement were skipped') if '465 skipped' in (P2/'CHANGELOG.md').read_text() else fails.append('skipped')

# ---------------- Mode F probe
fp=J('results/dock_F_probe.json')['summary']
pa_=fp['per_arm']
need('Mode F probe F1', [pa_[a]['F1'] for a in ['joint','sham_release','post_exit']],
     f"F1 Joint/sham/PostExit {f3(pa_['joint']['F1'])}/{f3(pa_['sham_release']['F1'])}/{f3(pa_['post_exit']['F1'])}; F2 {f3(pa_['joint']['F2'])}",
     f"F1 was {f3(pa_['joint']['F1'])} for Joint and sham but {f3(pa_['post_exit']['F1'])} for PostExit")
adv=fp['adverse']; f2ok=sum(1 for a in adv if a.get('F2', a['mirror']['median_first_exit_s'] in a['ns3_exits']))
need('Mode F adverse F2 (M5 split)', f2ok, f'F2 was 1.000 on the Amplification-2 cases but agreed in {f2ok}/{len(adv)} adverse-cell cases', f"F2 {f3(pa_['joint']['F2'])} (Amp-2), {f2ok}/{len(adv)} (adverse) & Fail")
cl=(P2/'CHANGELOG.md').read_text()
assert '1332 of 2355' in cl
need('state-change reports (changelog)', '1332/2355', 'triggered 1,332 of the 2,355 source reports in the 36 probe')

# ---------------- Mode F' (2b)
bp=J('results/dock2b_probe.json'); bh=J('results/dock2b_holdout.json'); b3=J('results/dock2b_F3_joint48.json')
bp=bp.get('summary',bp); bh=bh.get('summary',bh); b3=b3.get('summary',b3)
g=lambda d,a,k: d['per_arm'][a][k]
adv2=bp['adverse']; f2ok2=sum(1 for a in adv2 if a['F2'])
assert bh['adverse']==[]
need('2b probe F1 (in-sample, M1)', 0, f"On P (in-sample), F1 was {f3(g(bp,'joint','F1'))} (Joint), {f3(g(bp,'sham_release','F1'))} (sham), and {f3(g(bp,'post_exit','F1'))} (PostExit)",
     f"Mode F$'$ probe P (in-sample) & {bp['n']} & F1 {f3(g(bp,'joint','F1'))}/{f3(g(bp,'sham_release','F1'))}/{f3(g(bp,'post_exit','F1'))}; F2 {f3(g(bp,'joint','F2'))} (Amp-2), {f2ok2}/{len(adv2)} (adverse) & Fail",
     f"F2 was 1.000 on the Amplification-2 cases and agreed in {f2ok2}/{len(adv2)} adverse-cell cases")
need('2b holdout F1', bh['n'], f"On H, {bh['n']} cases", f"F1 was {f3(g(bh,'joint','F1'))}, {f3(g(bh,'sham_release','F1'))}, and {f3(g(bh,'post_exit','F1'))}",
     f"Mode F$'$ holdout H & {bh['n']} & F1 {f3(g(bh,'joint','F1'))}/{f3(g(bh,'sham_release','F1'))}/{f3(g(bh,'post_exit','F1'))}; F2 1.000 (Amp-2 only; H has no adverse cases)",
     f"holdout Joint agreement {f3(g(bh,'joint','F1'))} vs. 0.95")
assert all(g(d,a,'F2')==1.0 for d in (bp,bh) for a in ['joint','sham_release','post_exit'])
lo,hi=b3['mirror_interval_95']
need('2b F3 (M4 wording)', b3['ns3_joint_e1'], f"{b3['ns3_joint_e1']}/{b3['n']} lockouts were observed versus a predicted 95\\% interval of $[{lo}, {hi}]$ (expected {f2(b3['mirror_expected'])})",
     f"{b3['ns3_joint_e1']}/{b3['n']} observed vs.\\ predicted $[{lo},{hi}]$ (expected {f2(b3['mirror_expected'])}); Brier {f3(b3['brier'])}", f"with Brier score {f3(b3['brier'])}")
assert b3['inside'] is False and b3['n']==48
dg=J('results/dock2b_probe_diagnostic_E.json'); c=dg['per_run_contention']
need('2b contention', c, f"busy fraction {f3(c['mirror_cq']['busy_fraction'])} versus {f3(c['ns3']['busy_fraction'])}",
     f"NO\\_ACK jobs per run {thou(c['mirror_cq']['no_ack_jobs'])} versus {thou(c['ns3']['no_ack_jobs'])}",
     f"({c['mirror_cq']['channel_access_failures']} versus {c['ns3']['channel_access_failures']})")
m=re.match(r'(\d+)/(\d+)',dg['mirror_joint_reopen_cause']); need('2b reopen cause', m.group(0), f'({m.group(0)})')

# ---------------- FlockLab
fs=J('flocklab/results_full/summary.json')
assert fs['n_cases']==192 and fs['n_done']==192 and fs['n_failed']==0 and fs['audit_all_passed'] and fs['ingestion_audit_passed'] is False
need('FlockLab runs', 192, 'All 192 runs completed', '(192 runs')
ad=J('flocklab/results_full/audit_diagnostic_E.json')
need('R2 exact', ad['R2_exact'], f"every one of {thou(ad['R2_links'])} link-runs exactly", f"R2 {thou(ad['R2_exact'])}/{thou(ad['R2_links'])}")
need('R1 fail', ad['R1_fail'], f"{ad['R1_fail']} of {thou(ad['R1_tested'])} tested link-runs", f"{ad['R1_fail']}/{thou(ad['R1_tested'])}")
need('R1 expected', ad['R1_expected_exceedances_exact_binomial'], f"gives {f2(ad['R1_expected_exceedances_exact_binomial'])} expected exceedances")
ne=J('flocklab/results_neutral/summary.json')
ok=sum(all(x['hashes_equal'].values()) for x in ne['neutrality'])
need('neutrality', ok, f"byte-identically in {ok}/{len(ne['neutrality'])} cases")
tm=J('flocklab/traces/traces_meta.json'); sg=J('flocklab/traces/subgraphs.json')
need('Day A meta', tm['A'], f"Day~A, {tm['A']['day']} ({tm['A']['n_tests']} tests, {tm['A']['n_nodes']} nodes, {tm['A']['n_links']} directed links; {thou(tm['A']['n_unrecorded_rows'])} unrecorded rows")
need('Day B meta', tm['B'], f"Day~B, {tm['B']['day']} ({tm['B']['n_tests']} tests, {tm['B']['n_links']} directed links)")
need('subgraphs', [sg['A']['n_valid_assignments'],sg['A']['n_distinct_node_sets'],sg['B']['n_distinct_node_sets']],
     f"stopped at {thou(sg['A']['n_valid_assignments'])} valid assignments per day ({sg['A']['n_distinct_node_sets']} and {sg['B']['n_distinct_node_sets']} distinct node sets), from which {['zero','one','two','three','four'][len(sg['A']['subgraphs'])]} node sets")
assert sg['B']['n_valid_assignments']==sg['A']['n_valid_assignments'] and len(sg['B']['subgraphs'])==len(sg['A']['subgraphs'])
out=fs['outcomes']; key=lambda o:(o['day'],o['mode'],o['scenario'],o['arm'])
O={key(o):o for o in out}
ARM={'joint':'Joint','post_exit':'PostExit'}
for scen in ['M1','N']:
  for (day,mode) in [('A','R2'),('B','R2'),('A','R1')]:
    for arm in ['joint','post_exit']:
        o=O[(day,mode,scen,arm)]
        ml=mode+('$^{\\dagger}$' if mode=='R1' else '')
        row=f"{scen} & {day} & {ml} & {ARM[arm]} & {o['n']} & {o['with_unconfirmed_exit']} & {o['E1']} ({ci(o['E1'],o['n'])}) & {o['installs_after_exit_cases']} & {f3(o['median_worst_service'])} \\\\"
        need(f'S-table flock row {scen}-{day}-{mode}-{arm}', o, row)
M1=[o for o in out if o['scenario']=='M1']; N=[o for o in out if o['scenario']=='N']
jm=[o for o in M1 if o['arm']=='joint']; pm=[o for o in M1 if o['arm']=='post_exit']
nj=sum(o['n'] for o in jm); e1=sum(o['E1'] for o in jm); closed=sum(o['gate_closed'] for o in jm)
assert closed==nj and sum(o['installs_after_exit_cases'] for o in jm)==0
need('M1 Joint E1 total', e1, f"locked to the action deadline under the IU-only endpoint E1 in {e1}/{nj} (Wilson 95\\% CI {ci(e1,nj)})",
     f"Joint never reopened in {closed}/{nj} runs")
dn=J('flocklab/results_full/joint_nonE1_diagnostic_E.json')['summary']
assert dn['n_joint_M1']==nj and dn['E1']==e1 and dn['non_E1_any_allowed']==0 and dn['non_E1_fs_after_last_exit']==0 and dn['non_E1_with_missing_fresh_source']==dn['non_E1']
need('M10 non-E1 Joint explanation', dn['non_E1'], f"The other {dn['non_E1']} Joint runs also stayed closed", 'no admission was allowed and no eligible source-failure report appeared after the last exit',
     'mixed \\texttt{missing\\_fresh\\_source} with \\texttt{installation\\_unconfirmed}')
tl=J('flocklab/results_full/trace_length_diagnostic_E.json')
need('M10 trace wrap (main)', tl, f"{thou(tl['A']['R2_link_runs_wrapping'])} of {thou(tl['A']['R2_link_runs_with_frames'])} Day-A and {thou(tl['B']['R2_link_runs_wrapping'])} of {thou(tl['B']['R2_link_runs_with_frames'])} Day-B link-runs wrapped",
     f"by up to {tl['A']['max_evaluated_over_length']:.1f} and {tl['B']['max_evaluated_over_length']:.1f} passes")
need('M10 trace wrap (S-table footnote)', tl, f"Stream length per link: {tl['A']['stream_len_max']} strobes (Day~A), {tl['B']['stream_len_max']} (Day~B)",
     f"{thou(tl['A']['R2_link_runs_wrapping'])}/{thou(tl['A']['R2_link_runs_with_frames'])} (A), {thou(tl['B']['R2_link_runs_wrapping'])}/{thou(tl['B']['R2_link_runs_with_frames'])} (B)")
assert tl['A']['stream_len_min']==tl['A']['stream_len_max'] and tl['B']['stream_len_min']==tl['B']['stream_len_max']
pr=sum(o['installs_after_exit_cases'] for o in pm); pn=sum(o['n'] for o in pm)
assert sum(o['E1'] for o in pm)==0
need('M1 PostExit reopen', pr, f"PostExit reopened in {pr}/{pn} runs")
nn=sum(o['n'] for o in N); ne1=sum(o['E1'] for o in N)
need('N lockout', ne1, f"lockout was {ne1}/{nn}")
assert all(o['installs_after_exit_cases']==o['with_unconfirmed_exit'] for o in N)
ex=sorted({o['with_unconfirmed_exit'] for o in N}); need('N exits range', ex, f"in {ex[0]}--{ex[-1]} of 16 runs per cell")
gN=lambda d,mo,a: O[(d,mo,'N',a)]
assert gN('A','R2','joint')['median_worst_service']==gN('A','R2','post_exit')['median_worst_service']
assert gN('B','R2','joint')['median_worst_service']==gN('B','R2','post_exit')['median_worst_service']

# ---------------- DOE
ds=J('doe/summary.json'); pts=ds['points']
assert ds['n_cases']==432 and ds['n_done']==432 and ds['n_failed']==0 and ds['audit_all_passed']
need('DOE runs', 432, 'giving 432 runs', 'All 432 runs completed', 'registered 432-run fractional factorial')
need('DOE points', len(pts), f"The {len(pts)} design points")
h1=ds['H1']; need('H1', h1, f"H1 passed: {h1['gate_closed']}/{h1['eligible']} ({f3(h1['fraction'])})", f"H1 {h1['gate_closed']}/{h1['eligible']} \\textbf{{pass}}")
assert h1['pass'] is True
h2=ds['H2']; need('H2', h2, f"PostExit E1 occurred in {h2['E1']}/{h2['n']} runs", f"H2 {h2['E1']}/{h2['n']} \\textbf{{fail}}")
assert h2['pass_'] is False and ds['H3']['void'] is True
bad=[p for p in pts if p['postexit_E1']>0]; assert len(bad)==1; b=bad[0]
need('H2 point', b, f"drop window {int(b['drop_start'])}--{int(b['drop_end'])}~s, mask~{b['mask']}, late faults, wait {b['wait_s']}~s" if b['faults']==[[145,3],[225,6]] else 'MISMATCH')
tot_e1=sum(p['E1'] for p in pts); tot_ex=sum(p['exit'] for p in pts); tot_n=sum(p['n'] for p in pts)
need('DOE Joint E1 total', tot_e1, f"Joint E1 occurred in {tot_e1}/{tot_n} runs, and {tot_ex} Joint runs")
late=[p['exit'] for p in pts if p['drop_start']==240]
need('A=240 exits', (min(late),max(late)), f"exits were rare ({min(late)}--{max(late)} of 8 runs per point)")
me=ds['main_effects_joint']
lv=lambda f: ', '.join(f2(x['E1_rate']) for x in me[f])
need('main effect A', lv('A'), f"{lv('A').replace(', 0.07',', and 0.07')} for starts 0, 120, and 240~s" if True else '')
for f,txt in [('B','for 20, 60, 120~s'),('C','for masks 1, 2, 3'),('E','for 10, 15, 20~s')]:
    need(f'main effect {f}', lv(f), f"({lv(f)} {txt})")
need('main effect D', lv('D'), f"later relay faults ({lv('D')})")
assert all(x['n']==72 for f in me for x in me[f]); need('72 per level', 72, '72 runs per level')


# ---------------- registration-text constants (Phase-2b prereg) and rebuild spot check (changelog)
pre2b=(P2/'PREREG_PHASE2B_20261111.md').read_text()
for src,txt in [('FIFO queue 16','a 16-frame FIFO queue'),('minBE 3, maxBE 5, maxBackoffs 4','(minimum backoff exponent 3, maximum 5, at most 4 backoffs)'),
                ('(46.1 m)','a 46.1~m carrier-sense radius'),('(305 B/s, 4572 B, reserve 1524 B, 381 B per frame)','(305~B/s, 4,572~B burst, 1,524~B reserve, 381~B per frame)'),
                ('relay lease of 12 s','the 12~s relay lease'),('source 5/15 s rule','the source 5/15~s and relay 10/15~s report rules'),('relay 10/15 s rule','relay 10/15~s report rules'),
                ('Amp-2 layouts 2026110412–17 × 6 seeds × the same 3 arms = 108','six Amplification-2 layouts never used for calibration, development, or probing $\\times$ six inputs $\\times$ three arms')]:
    okc = (src in pre2b) and (txt in flat)
    checks.append({'label':f'2b constant: {src}','ok':okc})
    if not okc: fails.append('2b constant: '+src)
okr = ('MATCH 48/48 (480 files)' in cl) and ('A 48-case spot check reproduced the frozen Amplification-2 output files (480 files)' in flat)
checks.append({'label':'rebuild spot check 48/48 (480 files)','ok':okr})
if not okr: fails.append('rebuild spot check')

# ---------------- frozen numbers still present (unchanged)
for sn in ['0/96','26/48','26/26','59.29\\%','79.97\\%','2.95\\%','48/48','+20.68','23.02, 22.80, 22.61, and 22.14 percent','35.27 percent DATA reduction']:
    need(f'frozen number {sn}', sn, sn)
# ---------------- forbidden / conflicting wording removed
for bad_ in ['Verification is internal','no empirical validation against hardware data','not a new factorial sensitivity analysis','No hardware measurements are available in this study',
             'independent SimPy','independently written','independent implementation','not portable','gate decisions of all 248','decisions of all 248','survives measured','before any outcome was seen','including the Joint count of 26/48','Supplementary Notes S3;','Grok Bot was subsequently used']:
    okb = bad_ not in flat
    checks.append({'label':f'removed: {bad_}','ok':okb}); 
    if not okb: fails.append('removed: '+bad_)
# ---------------- expert revision M1-M10 / S-items: required wording (main text)
REQ=[('M1 post hoc 2b','designed after the Mode-F probe failure'),('M1 in-sample P','On P (in-sample)'),
     ('M2 holdout outcomes known','H is held out from model development, not blinded to outcomes'),('M3 diagnostic subsample','In a diagnostic subsample of four Joint probe cases $\\times$ 10 replicates'),
     ('M9 comparator cause','introduced after the original comparator flagged all 48 cases because the recorded controller hash embeds wall-clock fields'),('M9 post-outcome relaunch','a checkpointed relaunch during the Phase-2b holdout run'),
     ('R2 26/48 scope (reverify)','Their ns-3 outcomes (which contribute to the frozen Joint count of 26/48) were known'),
     ('opt1 abstract prevalence qualifier','(controlled recipe, not a prevalence estimate)'),
     ('opt3 Repository Notes','Repository Notes R1--R6'),
     ('opt5 declaration tool name from v0 original (t160u: Grok Bot, simpat_v0 l.490 / cb00e86)','and Grok Bot to assist with journal-scope research'),
     ('M3 not reproduced','not reproduced by the two abstract models tested'),('M3 alternative','We cannot exclude'),
     ('M6 separately coded','separately coded'),('M6 Mode C reproduces','reproduces the authorization state, reason class, and exit times'),
     ('M6 provenance','coded by the same AI agent as the Mode-C mirror'),
     ('M7 private repository','they were not lodged with a public registry'),
     ('M8 GenAI heading','Declaration of generative AI and AI-assisted technologies in the manuscript preparation process'),
     ('M8 placeholder TOOL','[TOOL NAME]'),('M8 placeholder VERSION','[VERSION]'),('M8 placeholder DEVELOPER','[DEVELOPER]'),
     ('M8 placeholder controller exposure','[STATEMENT ON CONTROLLER-SOURCE EXPOSURE'),('M8 placeholder earlier phases','[STATEMENT ON EARLIER PHASES'),
     ('M10 not external validation','Trace replay is not external validation of incidence'),
     ('S Table 10 footnote','The 432 factorial runs were registered for Mode C but not docked'),
     ('S Box 1','Box 1. Reusable V\\&V protocol'),('S H1/H2 conformance','conforms'),
     ('S DOI Kurkowski','10.1145/1096166.1096174'),('S DOI Pawlikowski','10.1109/35.978060'),('S DOI Andel','10.1109/MC.2006.242'),('S DOI Kleijnen','10.1016/0377-2217(94)00016-6'),
     ('S supplementary pointer','Supplementary Material (\\texttt{supplementary.pdf}) accompanies this article')]
for lab,sn in REQ:
    okq = sn in flat_main
    checks.append({'label':'required: '+lab,'snippet':sn,'ok':okq})
    if not okq: fails.append('required: '+lab)
# reverify: supplementary opening paragraph and cover letter
cov=re.sub(r'\s+',' ',(HERE/'cover_letter_DRAFT.txt').read_text())
for lab,sn,src in [('opt4 supp opening lists S9 and Fig. S1','Tables~S1--S5, S8, and S9 and Fig.~S1 were moved from the main text',flat_supp),
                   ('R1 cover letter in-sample design','its design was informed by the 44 probe cases, which are therefore in-sample; only the holdout is out-of-sample, although its outcomes were known before the Phase-2b registration.',cov),
                   ('R2 cover letter registration timing','registered before any run on registered inputs',cov),
                   ('R3 cover letter diagnosis','how source-failure evidence falls into report windows and MAC-level report phase',cov)]:
    okq = sn in src; checks.append({'label':'required: '+lab,'snippet':sn,'ok':okq})
    if not okq: fails.append('required: '+lab)
for bad_ in ['calibration is in-sample','registered before its full run']:
    okb = bad_ not in cov; checks.append({'label':'cover letter removed: '+bad_,'ok':okb})
    if not okb: fails.append('cover removed: '+bad_)
okd='$^{\\dagger}$' in flat_supp and 'R1$^{\\dagger}$' in flat_supp
checks.append({'label':'dagger on R1 rows (S-table)','ok':okd})
if not okd: fails.append('dagger R1')
# deposit claim must not be made for new artifacts
assert 'V\\&V package of Section~\\ref{sec:vv} is likewise \\emph{not} deposited' in flat
checks.append({'label':'Data Availability: V&V package not deposited','ok':True})

# ---------------- reverification round 3: Section 7.6 execution scale / cost numbers (compute_cost_E.json)
CE=J('compute_cost_E.json'); B=CE['batches']
nF=len(J('results/dock_F_probe.json')['rows']); n2p=len(J('results/dock2b_probe.json')['rows']); n2h=len(J('results/dock2b_holdout.json')['rows'])
need('7.6 docking case counts', (nF,n2p,n2h), f"ran {nF}, {n2p}, and {n2h} docking cases with {B['mode_fprime_holdout_108x100']['replications_per_case']} mirror replicates each")
need('7.6 run counts', (B['trace_replay_full_192']['runs'],B['factorial_432']['runs']), f"comprised {B['trace_replay_full_192']['runs']} ns-3 runs and the factorial {B['factorial_432']['runs']}")
need('7.6 machine', CE['machine'], f"one machine with {CE['machine']['logical_cpus']} logical CPUs and {CE['machine']['mem_gb']}~GB of memory")
need('7.6 replay third-launch span', B['trace_replay_full_192']['third_launch']['span_min'], f"spanned {B['trace_replay_full_192']['third_launch']['span_min']}~min ({B['trace_replay_full_192']['span_min']}~min if one case")
need('7.6 replay workers', B['trace_replay_full_192']['workers'], "The third replay launch (four worker processes)", "the third used four workers")
need('7.6 factorial span', B['factorial_432']['span_min'], f"the factorial (three workers, run concurrently with the replay) {B['factorial_432']['span_min']}~min")
assert B['factorial_432']['workers']==3
need('7.6 holdout span', B['mode_fprime_holdout_108x100']['span_min'], f"the Mode-F$'$ holdout {B['mode_fprime_holdout_108x100']['span_min']}~min")
need('7.6 output sizes', (B['trace_replay_full_192']['bytes'],B['factorial_432']['bytes']), f"{B['trace_replay_full_192']['bytes']/1e9:.2f}~GB (replay) and {B['factorial_432']['bytes']/1e9:.2f}~GB (factorial)")
inc=' '.join(CE['incidents'])
assert 'BrokenProcessPool' in inc and '2.3 GB RSS' in inc and '4 workers' in inc and '4 min in' in inc and 'dock2b_ckpt.py' in inc
need('7.6 incidents follow CHANGELOG order', 'replay x3 + holdout ckpt',
     "the first lost its worker pool when the launching shell exited, before any case started",
     "the second, with six workers, was stopped by the operating system's out-of-memory handler (one worker at 2.3~GB resident)",
     "was stopped after about 4~min and relaunched with a harness that writes per-case checkpoint files")
for bad_ in ['8 cores','a first launch of the replay with six workers','An earlier launch lost its worker pool']:
    okb = bad_ not in flat_main; checks.append({'label':'7.6 removed: '+bad_,'ok':okb})
    if not okb: fails.append('7.6 removed: '+bad_)
res={'status':'PASS' if not fails else 'FAIL','n_checks':len(checks),'fails':fails,'checks':checks,'no_simulation_run':True}
(HERE/'check_phase23_numbers.json').write_text(json.dumps(res,indent=1,default=str))
lines=[f"{'OK ' if c['ok'] else 'FAIL'}  {c['label']}" for c in checks]
(HERE/'check_phase23_numbers.txt').write_text('\n'.join(lines)+f"\n\n{res['status']}: {len(checks)-len(fails)}/{len(checks)} checks\n")
print('\n'.join(l for l in lines if l.startswith('FAIL')) or 'all OK'); print(res['status'], len(checks)-len(fails),'/',len(checks))
sys.exit(0 if not fails else 1)
