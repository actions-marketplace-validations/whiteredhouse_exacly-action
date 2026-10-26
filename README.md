# Exacly action

Runs [Exacly](https://github.com/whiteredhouse/exacly) in a repository's GitHub workflow. `check` validates the model and fails the job when it doesn't conform. `plan` comments a pull request's change plan, replacing its earlier comment. Both write their report to the job summary.

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
| `mode` | `check` | `check` validates the model; `plan` writes the change plan against the base branch and comments it. |
| `model` | `spec/exacly` | The model's config and state: files, folders or patterns such as `spec/exacly/*.yaml`, one per line or separated by spaces. Patterns are matched against each revision's files, so the plan sees files a change deleted. |
| `base` | the pull request's base branch | `plan`: the branch the change is against. |
| `token` | `github.token` | `plan`: the token that comments. It needs `pull-requests: write`. The earlier comment is found as `github-actions[bot]`'s, so with another token each run adds a comment. |

A pull request from a fork gets a read-only token, so its plan stays in the job summary. In private repositories, `plan` needs Git authentication to fetch the base branch: keep checkout's default `persist-credentials: true`, or configure Git authentication separately.

CI runs `check` on GitHub-hosted Linux and macOS runners, and `plan` on Linux. The action sets up uv itself; self-hosted runners also need Git, Bash and, for commenting, the GitHub CLI (`gh`).

## Versions

Pin a tag: `v0.4.0`, or the moving `v0` for the latest 0.x release. Each action release runs one release of the `exacly` package, pinned in [`pyproject.toml`](pyproject.toml) and installed from [`uv.lock`](uv.lock), so a release always validates the same way.

| Action | exacly | Spec versions it reads |
| --- | --- | --- |
| 0.1.0 | 0.1.0 (as `exacly-validate`) | 0.1, 0.2 |
| 0.2.0 | 0.2.1, from PyPI | 0.1, 0.2 |
| 0.3.0 | 0.3.0 | 0.1, 0.2 |
| 0.4.0 | 0.4.0 | 0.1, 0.2 |

The 0.4.0 action accepts supported verification before delivery and state with structured assessment subjects. It retains the existing inputs and the `check` and `plan` modes; it does not expose `assess` or `gate` modes.

## Development

The repository uses [mise](https://mise.jdx.dev/) for Python, uv, ShellCheck and tasks. Run what CI runs with `mise run check`.
