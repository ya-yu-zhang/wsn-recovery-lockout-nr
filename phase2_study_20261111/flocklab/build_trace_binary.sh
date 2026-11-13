#!/bin/bash
# Build the NEW FlockLab trace driver with conda GCC 14.4 against the rebuilt ns-3.44 libs.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
NS=/workspace/wsn_ablation/repo/ns3_vendor/ns-allinone-3.44/ns-3.44/build
ENG=/workspace/wsn_ablation/repo/control_budget_study_20261015/engine/ns3
CXX=/workspace/wsn_ablation/tc_env/bin/x86_64-conda-linux-gnu-g++
$CXX -std=c++20 -O2 -I $NS/include -I $ENG -I $HERE $HERE/wsn-closed-loop-trace.cc -L $NS/lib -Wl,-rpath,$NS/lib \
  -lns3.44-lr-wpan -lns3.44-spectrum -lns3.44-mobility -lns3.44-propagation -lns3.44-antenna -lns3.44-network -lns3.44-stats -lns3.44-core \
  -o $HERE/wsn-closed-loop-trace
sha256sum $HERE/wsn-closed-loop-trace $HERE/wsn-closed-loop-trace.cc $HERE/trace_link_error_model.h
