#!/bin/bash
# Passes the per-run FlockLab trace settings (set by common/ns3run.py) to the NEW trace binary.
# traceMode=0 (neutrality check): no trace options are passed (ns-3 CommandLine rejects an empty --traceFile=).
B="$(dirname "$0")/wsn-closed-loop-trace"
if [ "${PH2_TRACE_MODE:-0}" = "0" ]; then exec "$B" "$@"; fi
exec "$B" "$@" "--traceFile=${PH2_TRACE_FILE}" "--traceMode=${PH2_TRACE_MODE}" "--traceSeed=${PH2_TRACE_SEED}"
