# Exacly action

Runs [Exacly](https://github.com/whiteredhouse/exacly) in a repository's GitHub workflow. `check` validates the model and fails the job when it doesn't conform. `plan` comments a pull request's change plan, replacing its earlier comment. `gate` enforces a readiness policy for an explicit implementation target. Every mode writes its report to the job summary.

```yaml
# .github/workflows/exacly.yml
name: Exacly
on: pull_request
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: whiteredhouse/exacly-action@v0
        with:
          model: spec/exacly
  plan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    concurrency:
      group: exacly-plan-${{ github.event.pull_request.number }}
      cancel-in-progress: true
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: whiteredhouse/exacly-action@v0
        with:
          mode: plan
          model: spec/exacly
```

## Inputs

| Input | Default | What it does |
| --- | --- | --- |
| `mode` | `check` | `check` validates the model; `plan` writes the change plan against the base branch and comments it; `gate` enforces readiness. |
| `model` | `spec/exacly` | The model's config and state: files, folders or patterns such as `spec/exacly/*.yaml`, one per line or separated by spaces. Patterns are matched against each revision's files, so the plan sees files a change deleted. |
| `policy` | empty | `gate`: required path to one readiness policy YAML/JSON file. Paths containing spaces are supported. |
| `target` | empty | `gate`: required path to one explicit target YAML/JSON file. Paths containing spaces are supported. |
| `base` | the pull request's base branch | `plan`: the branch the change is against. |
| `token` | `github.token` | `plan`: the token that comments. It needs `pull-requests: write`. The earlier comment is found as `github-actions[bot]`'s, so with another token each run adds a comment. |

A pull request from a fork gets a read-only token, so its plan stays in the job summary. In private repositories, `plan` needs Git authentication to fetch the base branch: keep checkout's default `persist-credentials: true`, or configure Git authentication separately.

CI runs `check` and `gate` on GitHub-hosted Linux and macOS runners, and `plan` on Linux. The action sets up uv itself; self-hosted runners also need Git, Bash and, for commenting, the GitHub CLI (`gh`).

## Gate readiness

Gate mode is available from `v0.5.0`. Earlier action releases support `check` and `plan` only.

```yaml
- uses: whiteredhouse/exacly-action@v0.5.0
  with:
    mode: gate
    model: |
      spec/exacly/*.yaml
      reports/state/main.json
    policy: ci/verification.yaml
    target: reports/target.json
```

Run the observations before this step so the state and target identify the implementation you intend to assess. Keep policy and target files outside recursively loaded model folders. For example, a pre-release policy can require verification without requiring delivery:

```yaml
name: ci-verification
version: '1'
requirements:
  - record: REQ-001
    dimensions: [verification]
```

The target identifies the state context, model revision and implementation revision or build composition. See the [policy and target formats](https://github.com/whiteredhouse/exacly/blob/main/python/README.md#assess-an-implementation-target).

Gate mode fails unless every declared prerequisite is satisfied. It preserves the CLI exit statuses: `0` for satisfied, `1` for not satisfied or unknown, and `2` for invalid inputs. Missing policy/target inputs fail before package installation. The report includes the selected target, individual checks, evidence and reasons, in the logs and the job summary even when readiness is blocked or a file is invalid.

The action reads supplied observations; it does not run tests, refresh state, deploy, or infer delivery. Missing evidence leaves readiness unknown. Gate mode needs no write permissions or PR comment token. The default remains `check`; providing policy and target does not opt a workflow into gate mode unless `mode: gate` is selected.

## Versions

Pin a tag: `v0.5.0`, or the moving `v0` for the latest 0.x release. Each action release runs one release of the `exacly` package, pinned in [`pyproject.toml`](pyproject.toml) and installed from [`uv.lock`](uv.lock), so a release always validates the same way.

| Action | exacly | Spec versions it reads |
| --- | --- | --- |
| 0.1.0 | 0.1.0 (as `exacly-validate`) | 0.1, 0.2 |
| 0.2.0 | 0.2.1, from PyPI | 0.1, 0.2 |
| 0.3.0 | 0.3.0 | 0.1, 0.2 |
| 0.4.0 | 0.4.0 | 0.1, 0.2 |
| 0.5.0: opt-in readiness gates | 0.4.0 | 0.1, 0.2 |

The 0.4.0 action accepts supported verification before delivery and state with structured assessment subjects. It retains the existing inputs and the `check` and `plan` modes; it does not expose `assess` or `gate` modes.

## Development

The repository uses [mise](https://mise.jdx.dev/) for Python, uv, ShellCheck and tasks. Run what CI runs with `mise run check`.
