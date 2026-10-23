#!/usr/bin/env sh
set -eu
environment="$1"; api_digest="$2"; web_digest="$3"
test -n "$KUBE_CONFIG_DATA"
printf '%s' "$KUBE_CONFIG_DATA" | base64 -d > /tmp/nextleap-kubeconfig
export KUBECONFIG=/tmp/nextleap-kubeconfig
kubectl -n "nextleap-$environment" set image deployment/nextleap-api "api=ghcr.io/${GITHUB_REPOSITORY_OWNER}/nextleap-api@$api_digest"
kubectl -n "nextleap-$environment" rollout status deployment/nextleap-api --timeout=5m
kubectl -n "nextleap-$environment" set image deployment/nextleap-web "web=ghcr.io/${GITHUB_REPOSITORY_OWNER}/nextleap-web@$web_digest"
kubectl -n "nextleap-$environment" rollout status deployment/nextleap-web --timeout=5m
rm -f /tmp/nextleap-kubeconfig
