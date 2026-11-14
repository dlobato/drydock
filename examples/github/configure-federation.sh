#!/usr/bin/env bash
# Operator setup only. The provider stays disabled until the lab boundary passes.
set -euo pipefail

: "${DRYDOCK_PROJECT:?Set the existing Google project ID}"
: "${DRYDOCK_WORKFLOW_SHA:?Set the reviewed 40-character workflow commit on main}"
[[ "$DRYDOCK_WORKFLOW_SHA" =~ ^[0-9a-f]{40}$ ]] || exit 2

project_number=$(gcloud projects describe "$DRYDOCK_PROJECT" --format='value(projectNumber)')
pool=drydock-github
provider=pre-deployment
account="drydock-github@${DRYDOCK_PROJECT}.iam.gserviceaccount.com"
subject='repo:dlobato@1379455/drydock@1452964696:environment:gke'
condition="assertion.repository_id == '1452964696' && assertion.repository_owner_id == '1379455' && assertion.sub == '${subject}' && assertion.ref == 'refs/heads/main' && assertion.workflow_ref == 'dlobato/drydock/.github/workflows/pre-deployment.yml@refs/heads/main' && assertion.workflow_sha == '${DRYDOCK_WORKFLOW_SHA}' && assertion.event_name == 'workflow_dispatch'"

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project="$DRYDOCK_PROJECT"
gcloud iam workload-identity-pools create "$pool" --project="$DRYDOCK_PROJECT" \
  --location=global --display-name='Drydock approved GitHub jobs'
gcloud iam workload-identity-pools providers create-oidc "$provider" \
  --project="$DRYDOCK_PROJECT" --location=global --workload-identity-pool="$pool" \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id' \
  --attribute-condition="$condition" --disabled
gcloud iam service-accounts create drydock-github --project="$DRYDOCK_PROJECT" \
  --display-name='Drydock approved lab lifecycle'
gcloud iam service-accounts add-iam-policy-binding "$account" \
  --project="$DRYDOCK_PROJECT" --role=roles/iam.workloadIdentityUser \
  --member="principal://iam.googleapis.com/projects/${project_number}/locations/global/workloadIdentityPools/${pool}/subject/${subject}" \
  --format=none

# Cluster discovery is the only Google API operation granted to this account.
gcloud iam roles create drydockClusterConnection --project="$DRYDOCK_PROJECT" \
  --title='Drydock cluster connection' --permissions=container.clusters.get --stage=GA
gcloud projects add-iam-policy-binding "$DRYDOCK_PROJECT" \
  --member="serviceAccount:${account}" \
  --role="projects/${DRYDOCK_PROJECT}/roles/drydockClusterConnection" --condition=None --format=none

printf 'Provider (disabled): projects/%s/locations/global/workloadIdentityPools/%s/providers/%s\n' \
  "$project_number" "$pool" "$provider"
printf 'Service account: %s\n' "$account"
gcloud iam service-accounts describe "$account" --project="$DRYDOCK_PROJECT" \
  --format='value(uniqueId)'
