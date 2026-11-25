#!/usr/bin/env bash
set -euo pipefail

manifest="$(dirname "$0")/linux-tools.tsv"
bin_dir="$(mktemp -d)"
for tool in "$@"; do
  line="$(awk -v name="$tool" '$1 == name { print; found = 1 } END { if (!found) exit 1 }' "$manifest")"
  read -r name url digest member <<<"$line"
  curl --fail --silent --show-error --location --retry 3 --proto '=https' --proto-redir '=https' "$url" -o "$bin_dir/download"
  printf '%s  %s\n' "$digest" "$bin_dir/download" | sha256sum --check --status
  if [[ "$member" == "-" ]]; then
    mv "$bin_dir/download" "$bin_dir/$name"
  else
    tar -xzOf "$bin_dir/download" "$member" >"$bin_dir/$name"
  fi
  chmod 755 "$bin_dir/$name"
done
echo "$bin_dir" >>"$GITHUB_PATH"
