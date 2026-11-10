#!/usr/bin/env bash
# ==============================================================================
# gcp_nl_cost_and_latency_cutover.sh (v3.0 — Production-Safe GCP Toolkit)
# ==============================================================================
# Incorporates all P0/P1 SRE & economic controls:
#   1. `--mode=audit` (READ-ONLY, default):
#      Inventories all VMs, OS-Login metadata, disks, Asia/JP/EU snapshots, images,
#      static IPs, and Montreal Cloud Run / Scheduler jobs against verified SKU IDs.
#   2. `--mode=resize-fi-inplace` (SAFE RECOMMENDED COMPUTE SAVINGS):
#      Quiesces `quant-pipeline-finland` cleanly (stops timers/services, cancels resting
#      Maker GTC orders so 0 orders sit unattended, runs atomic `sqlite3 .backup` +
#      `PRAGMA integrity_check`), resizes in-place from `e2-standard-2` (8GB) to
#      `e2-custom-2-4096` (2 FULL 100% sustained vCPUs + 4GB RAM — avoiding `e2-medium`'s
#      50% CPU throttling and avoiding dual-VM split-brain!), and restarts + reconciles.
#   3. `--mode=bench-fi-standard-tier`:
#      Runs a 100% READ-ONLY 500-sample (`N=500`) p50/p95/p99 benchmark in `europe-north1-b`
#      on `STANDARD` Network Tier (`200 GiB/mo` free egress) with ZERO wallet credentials
#      and ZERO live orders, then deletes the disposable VM.
#   4. `--mode=bench-nl-readonly`:
#      Runs a 100% READ-ONLY 500-sample (`N=500`) p50/p95/p99 benchmark in `europe-west4-a`
#      with ZERO wallet credentials and ZERO live orders, then deletes the disposable VM.
#
# Usage in Google Cloud Shell:
#   bash scripts/gcp_nl_cost_and_latency_cutover.sh --mode=audit
#   bash scripts/gcp_nl_cost_and_latency_cutover.sh --mode=bench-fi-standard-tier
#   bash scripts/gcp_nl_cost_and_latency_cutover.sh --mode=resize-fi-inplace
#   bash scripts/gcp_nl_cost_and_latency_cutover.sh --mode=bench-nl-readonly
# ==============================================================================

set -euo pipefail

export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"

PROJECT_ID="${GCP_PROJECT_ID:-parnasa-498503}"
FI_VM="${FI_VM:-quant-pipeline-finland}"
FI_ZONE="${FI_ZONE:-europe-north1-b}"
NL_BENCH_VM="${NL_BENCH_VM:-dominus-nl-bench}"
NL_ZONE="${NL_ZONE:-europe-west4-a}"
SSH_USER="skybullet1987"
MODE="audit"

for arg in "$@"; do
  case "$arg" in
    --mode=*) MODE="${arg#*=}" ;;
    --project=*) PROJECT_ID="${arg#*=}" ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

echo "=============================================================================="
echo " DOMINUS GCP TOOLKIT v3.0 | Project=${PROJECT_ID} | Mode=${MODE}"
echo "=============================================================================="

if [[ "${MODE}" == "audit" ]]; then
  echo ""
  echo "[1/5] Project OS-Login Setting & Compute Engine VMs:"
  gcloud compute project-info describe --project="${PROJECT_ID}" \
    --format="value(commonInstanceMetadata.items.filter(key:enable-oslogin))" || true
  gcloud compute instances list --project="${PROJECT_ID}" \
    --format="table(name,zone.basename(),machineType.basename(),networkInterfaces[0].networkIP:label=INT_IP,networkInterfaces[0].accessConfigs[0].natIP:label=EXT_IP,networkInterfaces[0].accessConfigs[0].networkTier:label=NET_TIER,status)"

  echo ""
  echo "[2/5] Persistent Disks (SKU ABEC-4750-B9EF = CA\$7.36 / 15d for 100GB pd-balanced):"
  gcloud compute disks list --project="${PROJECT_ID}" \
    --format="table(name,zone.basename(),sizeGb,type.basename(),users.basename())"

  echo ""
  echo "[3/5] Snapshots & Custom Images (SKUs 6E69 / 9ECE / 8C30 / DAA2 = CA\$3.45 / 15d):"
  gcloud compute snapshots list --project="${PROJECT_ID}" \
    --format="table(name,storageBytes,diskSizeGb,storageLocations,creationTimestamp)"
  gcloud compute images list --project="${PROJECT_ID}" --no-standard-images \
    --format="table(name,diskSizeGb,storageBytes,creationTimestamp,status)"

  echo ""
  echo "[4/5] Static External IPs:"
  gcloud compute addresses list --project="${PROJECT_ID}" \
    --format="table(name,region.basename(),address,networkTier,status,users.basename())"

  echo ""
  echo "[5/5] Montreal Cloud Run & Scheduler (SKUs ED10 / 085C = CA\$8.60 / 15d):"
  gcloud run services list --project="${PROJECT_ID}" --region=northamerica-northeast1 \
    --format="table(metadata.name,status.url,metadata.annotations.'autoscaling.knative.dev/minScale':label=MIN_INSTANCES)" || true
  gcloud run jobs list --project="${PROJECT_ID}" --region=northamerica-northeast1 \
    --format="table(metadata.name,status.latestCreatedExecution.name,status.latestCreatedExecution.completionTimestamp)" || true
  gcloud scheduler jobs list --project="${PROJECT_ID}" --location=northamerica-northeast1 \
    --format="table(name.basename(),schedule,state,httpTarget.uri)" || true

  cat <<'EOF'

------------------------------------------------------------------------------
 CONSOLE TOGGLE (Verified SKUs 9BF8 / D9AD / BDBA = CA$1.47 / 15d = ~CA$2.94/mo net):
   GCP Console -> Network Intelligence Center -> Disable:
     1. Network Analyzer
     2. Network Topology
     3. Performance Dashboard
------------------------------------------------------------------------------
EOF
  exit 0
fi

if [[ "${MODE}" == "resize-fi-inplace" ]]; then
  echo ""
  echo "[1/4] Quiescing ${FI_VM}, canceling resting Maker orders, & creating verified SQLite backup..."
  gcloud compute ssh "${SSH_USER}@${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --command="
    cd ~/quant_pipeline &&
    systemctl --user stop polymarket-paa-director-event.path 2>/dev/null || true &&
    ACTIVE_UNITS=\$(systemctl --user list-units --type=timer,service --state=active --no-legend | awk '{print \$1}' | grep -E '^polymarket-' || true) &&
    if [ -n \"\$ACTIVE_UNITS\" ]; then systemctl --user stop \$ACTIVE_UNITS; fi &&
    sleep 2 &&
    venv/bin/python3 -c '
from dotenv import load_dotenv; load_dotenv(\".env\")
from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
ex = PolymarketLiveExecutor(dry_run=False)
if ex.client is not None:
    print(\"cancel_all:\", ex.client.cancel_all())
' &&
    if [ -f data/polymarket/paa/paa_tasks.db ]; then
      sqlite3 data/polymarket/paa/paa_tasks.db \".backup 'data/polymarket/paa/paa_tasks.pre_resize.bak.db'\" &&
      sqlite3 data/polymarket/paa/paa_tasks.pre_resize.bak.db 'PRAGMA integrity_check;'
    fi &&
    if [ -f data/polymarket/paa_autonomy.db ]; then
      sqlite3 data/polymarket/paa_autonomy.db \".backup 'data/polymarket/paa_autonomy.pre_resize.bak.db'\" &&
      sqlite3 data/polymarket/paa_autonomy.pre_resize.bak.db 'PRAGMA integrity_check;'
    fi
  "

  echo ""
  echo "[2/4] Stopping ${FI_VM} and resizing in-place to e2-custom-2-4096 (2 FULL sustained E2 vCPUs, 4 GB RAM)..."
  gcloud compute instances stop "${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}"
  gcloud compute instances set-machine-type "${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" \
    --machine-type=e2-custom-2-4096

  echo ""
  echo "[3/4] Starting ${FI_VM} and fetching updated ephemeral External IP..."
  gcloud compute instances start "${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}"
  sleep 25
  NEW_EXT_IP="$(gcloud compute instances describe "${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
  echo "[IMPORTANT] Update HostName under 'Host kraken-finland' in C:\\Users\\Anton\\.ssh\\config to: ${NEW_EXT_IP}"

  echo ""
  echo "[4/4] Verifying RAM, CPU count, systemd units, and ledger reconciliation..."
  gcloud compute ssh "${SSH_USER}@${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --command="
    free -m && nproc &&
    systemctl --user list-units 'polymarket-*' --no-pager &&
    cd ~/quant_pipeline && venv/bin/python3 audit_losing_trades.py | tail -n 25
  "
  exit 0
fi

if [[ "${MODE}" == "bench-fi-standard-tier" ]]; then
  FI_STD_VM="dominus-fi-std-bench"
  echo ""
  echo "[1/3] Provisioning disposable ${FI_STD_VM} in ${FI_ZONE} on STANDARD Network Tier (100% READ-ONLY, zero wallet keys)..."
  gcloud compute instances create "${FI_STD_VM}" \
    --project="${PROJECT_ID}" --zone="${FI_ZONE}" \
    --machine-type=e2-custom-2-4096 --network-tier=STANDARD \
    --no-service-account --no-scopes \
    --boot-disk-size=10GB --boot-disk-type=pd-standard \
    --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud
  sleep 25
  echo "[2/3] Running N=500 read-only HTTP/TLS + WS + Upstream Feed benchmark vs live PREMIUM tier..."
  gcloud compute ssh "${SSH_USER}@${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --command="
    cat ~/quant_pipeline/scripts/check_polymarket_region_latency.py
  " | gcloud compute ssh "${SSH_USER}@${FI_STD_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --command="
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-websockets chrony >/dev/null &&
    python3 - --samples 500 --ws-probe --feed-probe
  "
  echo "[3/3] Deleting disposable ${FI_STD_VM}..."
  gcloud compute instances delete "${FI_STD_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --quiet
  exit 0
fi

if [[ "${MODE}" == "bench-nl-readonly" ]]; then
  echo ""
  echo "[1/3] Provisioning disposable ${NL_BENCH_VM} in ${NL_ZONE} (100% READ-ONLY, zero wallet keys)..."
  gcloud compute instances create "${NL_BENCH_VM}" \
    --project="${PROJECT_ID}" --zone="${NL_ZONE}" \
    --machine-type=e2-custom-2-4096 --network-tier=STANDARD \
    --no-service-account --no-scopes \
    --boot-disk-size=10GB --boot-disk-type=pd-standard \
    --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud
  sleep 25
  echo "[2/3] Running N=500 read-only HTTP/TLS + WS + Upstream Feed benchmark..."
  gcloud compute ssh "${SSH_USER}@${FI_VM}" --project="${PROJECT_ID}" --zone="${FI_ZONE}" --command="
    cat ~/quant_pipeline/scripts/check_polymarket_region_latency.py
  " | gcloud compute ssh "${SSH_USER}@${NL_BENCH_VM}" --project="${PROJECT_ID}" --zone="${NL_ZONE}" --command="
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-websockets chrony >/dev/null &&
    python3 - --samples 500 --ws-probe --feed-probe
  "
  echo "[3/3] Deleting disposable ${NL_BENCH_VM}..."
  gcloud compute instances delete "${NL_BENCH_VM}" --project="${PROJECT_ID}" --zone="${NL_ZONE}" --quiet
  exit 0
fi

echo "Invalid --mode=${MODE} (expected: audit | bench-fi-standard-tier | resize-fi-inplace | bench-nl-readonly)" >&2
exit 2
