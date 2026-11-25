#!/usr/bin/env bash
set -euo pipefail
check=$1
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
git init -q
git config user.name CI
git config user.email ci@example.invalid
mkdir module other
echo 'BasedOnStyle: LLVM' >.clang-format
printf 'int  legacy;\n\nint untouched;\n' >module/source.c
git add .
git commit -qm baseline
base=$(git rev-parse HEAD)

echo 'int introduced;' >>module/source.c
echo 'int   out_of_scope;' >other/other.c
git add .
git commit -qm clean
cd module
bash "$check" "$base"

echo 'int    new_violation;' >>source.c
git commit -qam violation
if bash "$check" "$base" >"$work/patch"; then
  echo 'Expected the changed-line formatting violation to fail' >&2
  exit 1
fi
grep -Fx '+int new_violation;' "$work/patch"
