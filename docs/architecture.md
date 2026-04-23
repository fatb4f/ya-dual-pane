# Architecture

## Authority split

- **Kitty** owns layout and focus hints
- **Yazi DDS** owns the wire contract
- **Coordinator** owns authority, lease, ordering, and rejection
- **CUE** owns declarative policy
- **Neovim** remains an optional side-effect adapter

## Core invariants

1. Preserve the DDS envelope shape on the wire.
2. Keep participant identity separate from pane placement.
3. Allow only the coordinator to publish committed shared truth.
4. Keep local browsing local until policy promotes it.

## Runtime topology

```text
Yazi primary ----\
                  \
Yazi peer ---------> coordinator ----> authoritative outcomes
                  /
Kitty focus hints /

coordinator ----> optional editor adapter
```

## Event classes

### DDS wire event

Canonical envelope:

- `kind`
- `receiver`
- `sender`
- `body`

### Authority sidecar

Layered metadata:

- `event_id`
- `origin_seq`
- `lease_epoch`
- `participant_id`
- `commit_seq`
- `decision`

## Live state

The coordinator tracks:

- current lease holder
- current lease epoch
- last accepted sequence per participant
- dedupe cache for event IDs
- monotonic commit sequence
