# ya-dual-pane

Dual-pane Yazi workflow around two symmetric Yazi instances, a fixed two-pane Kitty layout, and Yazi DDS as the wire contract.

## Current staging target

This stage implements the **coordinator event loop skeleton** first.

It establishes the authority boundary before any Kitty pane-mode shell is wired on top:

- DDS envelope is the wire oracle: `kind`, `receiver`, `sender`, `body`
- participant identity is stable and separate from left/right placement
- the coordinator owns lease, epoch, sequence checks, and commit/reject flow
- CUE policy files define the declarative contract
- the runtime currently loads a JSON mirror of that policy until `cue export` is wired in

## Repository layout

```text
.
├── README.md
├── pyproject.toml
├── bin/
│   └── ya-coord
├── cue.mod/
│   └── module.cue
├── docs/
│   ├── architecture.md
│   ├── coordinator.md
│   └── milestones.md
├── examples/
│   ├── ingress.jsonl
│   └── expected-outcomes.jsonl
├── policy/
│   ├── lease.cue
│   ├── participants.cue
│   └── routing.cue
├── profiles/
│   └── dev.cue
├── runtime/
│   └── policy.dev.json
├── schema/
│   ├── authority.cue
│   ├── dds.cue
│   └── outcome.cue
├── src/
│   └── ya_dual_pane/
│       ├── __init__.py
│       ├── cli.py
│       ├── coordinator.py
│       ├── dds.py
│       ├── policy.py
│       └── types.py
└── tests/
    └── test_coordinator.py
```

## Coordinator skeleton scope

The staged coordinator already does the following:

- parses DDS wire envelopes from either structured JSON or raw `kind,receiver,sender,body` lines
- maps Yazi sender IDs to stable participant IDs
- validates sender identity against the runtime policy
- enforces current lease holder and lease epoch
- enforces monotonic per-origin sequence numbers
- suppresses duplicate event IDs
- rejects policy-illegal addressed self-targets
- emits structured `commit`, `reject`, or `ignore` outcomes as JSON lines

## Runtime model

The coordinator keeps a small in-memory live state:

- `lease_holder`
- `lease_epoch`
- `last_seq_by_participant`
- `seen_event_ids`
- `commit_seq`

## Running the skeleton

### Run tests

```bash
python -m unittest discover -s tests -v
```

### Run the coordinator against the sample stream

```bash
PYTHONPATH=src python -m ya_dual_pane.cli run \
  --policy runtime/policy.dev.json \
  < examples/ingress.jsonl
```

### Run via the helper wrapper

```bash
PYTHONPATH=src bin/ya-coord run --policy runtime/policy.dev.json < examples/ingress.jsonl
```

## Input format

The runtime accepts one JSON object per line.

Each line may provide either:

1. a structured wire object:

```json
{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp"}},"meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":1}}
```

2. or a raw DDS payload string:

```json
{"wire_raw":"hover,0,100,{\"tab\":0,\"url\":\"/tmp\"}","meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":1}}
```

## Notes on CUE

CUE files in `schema/`, `policy/`, and `profiles/` define the intended declarative authority plane.

The current Python runtime does **not** evaluate CUE directly yet because the `cue` tool is not bootstrapped in this stage. Instead, it reads `runtime/policy.dev.json`, which mirrors the staged CUE profile.

The next policy integration step is:

- `cue export profiles/dev.cue > runtime/policy.dev.json`
- then make the runtime treat that JSON as generated, not hand-authored

## Next stage

After this skeleton is validated, the next correct layer is the Kitty pane-mode shell bound against this contract:

- pane spawn / close
- stable placement map
- focus hints
- maximize / restore
