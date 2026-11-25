# Keep the original CodeQL run. This second label lets GitHub compare both
# the canonical configuration and an existing workflow-derived baseline.
($legacy | rtrimstr("/")) as $previous
| if ($previous | test("^\\.github/workflows/[A-Za-z0-9_.-]+\\.ya?ml:[^[:space:][:cntrl:]]+\\z") | not) then
    error("expected a previous GitHub workflow category")
  elif (.runs | length) != 1 or .runs[0].tool.driver.name != "CodeQL"
       or .runs[0].automationDetails.id != $canonical then
    error("expected one CodeQL run with the requested language category")
  else
    .runs += [(.runs[0] | .automationDetails.id = ($previous + "/"))]
  end
