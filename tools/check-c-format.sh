#!/usr/bin/env bash
set -euo pipefail

# clang-format discovers a style relative to each source. Opt in at the project
# root or component level without picking up configuration outside the checkout.
root=$(git rev-parse --show-toplevel)
directory=$(pwd -P)
while [[ ! -f "$directory/.clang-format" && ! -f "$directory/_clang-format" ]]; do
  [[ "$directory" != "$root" && "$directory" != / ]] || exit 0
  directory=$(dirname "$directory")
done

base=${1:?expected the commit to compare against HEAD}
if [[ "$base" == 0000000000000000000000000000000000000000 ]]; then
  # The first push of a new default branch has no previous commit.
  git ls-files -z -- '*.c' '*.h' | xargs -0 -r clang-format --dry-run --Werror --
else
  git clang-format --style file --extensions c,h --diff "$base" HEAD -- .
fi
