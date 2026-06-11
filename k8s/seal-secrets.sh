#!/usr/bin/env bash
# Seal Decision Court's secrets into k8s/sealedsecret.yaml.
# Requires: kubeseal pointed at this cluster's sealed-secrets controller.
# Nothing plaintext is ever written to git — only the sealed (ciphertext) output.
set -euo pipefail

: "${GROQ_API_KEY:?export GROQ_API_KEY first (the Decision Court project key)}"
: "${POSTGRES_PASSWORD:?export POSTGRES_PASSWORD first (choose a strong one)}"

DATABASE_URL="postgresql+asyncpg://decisioncourt:${POSTGRES_PASSWORD}@decision-court-db:5432/decisioncourt"
DIR="$(cd "$(dirname "$0")" && pwd)"

kubectl create secret generic decision-court-secrets \
  --namespace decision-court \
  --from-literal=GROQ_API_KEY="${GROQ_API_KEY}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=DATABASE_URL="${DATABASE_URL}" \
  --dry-run=client -o yaml |
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets-controller \
  --scope cluster-wide \
  --format yaml > "${DIR}/sealedsecret.yaml"

echo "Wrote ${DIR}/sealedsecret.yaml — safe to commit. Verify it contains encryptedData, not plaintext."
