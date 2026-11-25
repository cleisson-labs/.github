#!/usr/bin/env bash
set -euo pipefail

# Include hidden directories and safely handle filenames containing whitespace.
git ls-files -z -- '*.sh' '*.bash' | xargs -0 -r shellcheck --
if [[ -n "${BASE_SHA:-}" && "$BASE_SHA" != 0000000000000000000000000000000000000000 ]]; then
  git diff --diff-filter=ACMR --name-only -z "$BASE_SHA" HEAD -- '*.sh' '*.bash' | xargs -0 -r shfmt -i 2 -d --
fi
