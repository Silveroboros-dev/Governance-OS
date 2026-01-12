# Branch protection checklist (recommended)

This project relies on discipline to prevent “UX-washing” and nondeterministic drift.

## Branches
- `main`: protected (release/pilot-ready)
- `dev`: optional (integration branch)

## Protect `main`
Enable:
- Require pull request before merging
- Require approvals: 1 (solo: self-review still works via PR discipline)
- Require status checks to pass
  - backend tests
  - frontend lint/tests
  - type checks (if used)
- Require linear history (recommended)
- Require conversation resolution before merging
- Do not allow force pushes
- Do not allow deletions

## Optional hardening
- Require signed commits
- Require CODEOWNERS review
- Dismiss stale approvals when new commits are pushed

## Release hygiene (lightweight)
- Tag releases (e.g., `v0.1.0-pilot`)
- Keep a short `CHANGELOG.md` for pilot-facing changes
