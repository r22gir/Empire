# SimulaLab Phase 1

SimulaLab is Empire's native, CPU-safe dataset/eval pilot for routing MAX requests across MAX, Hermes, OpenClaw, and supporting Empire tools. Phase 1 is deterministic and synthetic. It does not clone or depend on Google Simula, OpenSimula, AfterImage, CUDA, vLLM, cloud APIs, or local model downloads.

OpenSimula and AfterImage are future optional adapter ideas only. They are not required for this pilot.

## Dataset

- Dataset id: `max_command_routing_v1`
- Domain: `max_command_routing`
- Generator: `deterministic_internal_v1`
- Intended use: `eval_only`
- Schema version: `1.0`
- Default output root: `/data/empire/simula`

The generator creates JSONL rows with expected routing labels for runtime truth checks, commit/push/live verification, MAX channel continuity, OpenClaw code-task delegation, Hermes boundaries, ArchiveForge/RecoveryForge truth, photo upload/capture checks, Quote to Invoice to Payment regression discipline, ApostApp status, local fallback behavior, user frustration handling, service restart caution, and protected module caution.

## Hermes Compatibility

The dataset encodes these boundaries:

- MAX may use Hermes for memory, draft, form-prep, read-only lookup support, and staged browser-assist planning.
- MAX must use OpenClaw for code changes, tests, commits, pushes, service restarts, and runtime fixes.
- Hermes browser actions require explicit founder approval.
- Hermes must not submit forms, send messages, or claim execution without approval and evidence.
- Hermes output is supporting context only, beneath runtime truth, registry truth, and repo truth.

## Commands

Generate the default dataset:

```bash
python scripts/simula_lab_smoke.py --dataset max_command_routing_v1 --count 25
```

Generate into a temporary root:

```bash
python scripts/simula_lab_smoke.py --dataset max_command_routing_v1 --count 25 --output-root /tmp/empire-simula-test
```

Validate without writing files:

```bash
python scripts/simula_lab_smoke.py --dataset max_command_routing_v1 --count 25 --dry-run
```

## Outputs

The smoke command creates these directories when writing:

- `/data/empire/simula/datasets`
- `/data/empire/simula/manifests`
- `/data/empire/simula/reports`
- `/data/empire/simula/taxonomies`
- `/data/empire/simula/eval_runs`

For `max_command_routing_v1`, the primary outputs are:

- `/data/empire/simula/datasets/max_command_routing_v1.jsonl`
- `/data/empire/simula/manifests/max_command_routing_v1.manifest.json`
- `/data/empire/simula/reports/max_command_routing_v1.report.json`

## Validation

Validation checks that JSONL parses, required fields are present, routing enums are valid, `synthetic` is true, `intended_use` is `eval_only`, `schema_version` is `1.0`, and generated rows do not include obvious secret markers.

Phase 1 is an eval generator only. It does not modify live MAX chat behavior, OpenClaw runtime behavior, frontend UI, services, or product runtime code.
