"""Stage definitions for Amplification-2 (second pre-registration attempt).

Attempt 1 (AMPLIFICATION_PREREG_20261103 / CONFIRM_REPORT_20261104) failed S1
with Joint lockout 0/96. This file freezes the *mechanism change*: gateway-timed
install-packet drop (dropInstall*), geometry-decoupled from d(4,0) / overload+R0.
"""
# Attempt-1 layouts/seeds must not be reused for confirmatory claims.
AMP1_CONFIRM_LAYOUTS = {
    2026110306, 2026110309, 2026110310, 2026110319, 2026110324, 2026110327,
    2026110328, 2026110331, 2026110334, 2026110336, 2026110338, 2026110340,
    2026110307, 2026110311, 2026110318, 2026110320,
}
DEV_LAYOUTS = {2026101501, 2026101521, 2026101522, 2026101523,
               2026110301, 2026110302, 2026110303, 2026110304}

ARMS = ('joint', 'post_exit', 'sham_release', 'wait_extend',
        'fs_relax_scoped', 'thresh_relax_scoped', 'fs_relax_global', 'thresh_relax_global')

# Primary frozen recipe: timed gateway drop of install packets to BOTH sources.
# start=0, end=200 s, mask=3. No data-relay fault schedule (empty): induction is
# the drop itself, not weak control-hop geometry.
M1 = dict(
    # Primary induction = gateway timed install drop (geometry-free).
    # Downstream relay removals (3 then 6; node 2 kept) are pre-registered
    # service-harm backdrop for S2; they are NOT the confirmation-loss cause.
    recipe='M1_drop_both_0_200_dn36',
    scenario='multi_failure',
    faults=[[145, 3], [225, 6]],
    drop_install_start_sec=0.0,
    drop_install_end_sec=200.0,
    drop_install_mask=3,
)

# Appendix alternative (not primary): asymmetric drop of source-0 installs only,
# plus late downstream relay removals (nodes 3 then 6) for service harm while
# keeping source-first-hop (node 2) up — F_s-blind path degradation candidate.
M2_ALT = dict(
    recipe='M2_drop_src0_0_200_downstream',
    scenario='multi_failure',
    faults=[[145, 3], [225, 6]],
    drop_install_start_sec=0.0,
    drop_install_end_sec=200.0,
    drop_install_mask=1,
)

# --- manip_check: 4 fresh layouts × 2 input seeds × {joint, post_exit} = 16 ---
MANIP_LAYOUTS = (2026110401, 2026110402, 2026110403, 2026110404)
MANIP_SEEDS = (2026110601, 2026110602)
MANIP_ARMS = ('joint', 'post_exit')


def manip_check():
    m = M1
    out = []
    for L in MANIP_LAYOUTS:
        assert L not in AMP1_CONFIRM_LAYOUTS | DEV_LAYOUTS
        for sd in MANIP_SEEDS:
            for a in MANIP_ARMS:
                out.append(dict(
                    topology=f'budget_10_{L}', scenario=m['scenario'], seed=sd,
                    recipe=m['recipe'], faults=m['faults'], arm=a,
                    drop_install_start_sec=m['drop_install_start_sec'],
                    drop_install_end_sec=m['drop_install_end_sec'],
                    drop_install_mask=m['drop_install_mask'],
                    stratum='manip_check',
                ))
    return out


# --- confirm (frozen; do not run until manip_check pass criteria met) ---
CONFIRM_LAYOUTS = (2026110410, 2026110411, 2026110412, 2026110413,
                   2026110414, 2026110415, 2026110416, 2026110417)
CONFIRM_SEEDS = tuple(range(2026110611, 2026110617))  # 6 inputs


def confirm():
    m = M1
    out = []
    for L in CONFIRM_LAYOUTS:
        assert L not in AMP1_CONFIRM_LAYOUTS | DEV_LAYOUTS | set(MANIP_LAYOUTS)
        for sd in CONFIRM_SEEDS:
            for a in ARMS:
                out.append(dict(
                    topology=f'budget_10_{L}', scenario=m['scenario'], seed=sd,
                    recipe=m['recipe'], faults=m['faults'], arm=a,
                    drop_install_start_sec=m['drop_install_start_sec'],
                    drop_install_end_sec=m['drop_install_end_sec'],
                    drop_install_mask=m['drop_install_mask'],
                    stratum='confirm',
                ))
    return out


STAGES = {'manip_check': manip_check, 'confirm': confirm}
