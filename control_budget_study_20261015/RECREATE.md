# Recreate the isolated mechanism study

The base engine is the same_state_diagnosis_20261013 directory at repository commit3d30817f7d7dbc4e5a160d9e6981429b19c25805. Copy that directory to control_budget_study_20261015/engine, preserving the new unified_control_budget.h supplied here. Run prepare_engine.py once against the unchanged base copy. This produces the isolated modified engine; the historical engine remains unchanged.

Clone the official ns-3 Git source at tag ns-3.44 into the repository root ns3_vendor/ns-allinone-3.44/ns-3.44. Its pinned commit is43dce6710b8df69685e3479c1d33a571dda714ea. Install cmake and ninja using pip --target build_tools one directory above the repository. build_environment.py documents all flags and records the actual native binary hash. It checks for and rebuilds any empty object files without changing ns-3 sources.

Run run_study.py --stage functional --register-only before experiments, then the functional stage. Repeat registration and execution for development. Confirmation is admitted only after the frozen development service/cost checks pass. The mechanism protocol, actual source hashes, configuration lists and audit results are distinct from publication readiness. Results are not claimed before they exist.
