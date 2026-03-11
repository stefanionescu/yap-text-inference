# Notes

- Local SonarQube is provisioned by the repo scripts; admin credentials and the
  analysis token live in `.cache/security/sonarqube/`.
- This repo scans Python source and repo-owned operational code, including
  `src/`, `scripts/`, `linting/`, and `tests/`.
- Coverage and test artifacts are generated from `bash scripts/coverage.sh`.
- Quality gate and quality profile configuration are provisioned server-side by
  `linting/security/sonarqube/server.sh ensure`.
- Dashboard: `{{SONAR_DASHBOARD_URL}}`
