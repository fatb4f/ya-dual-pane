# Coordinator skeleton

## Goal

Establish the authority boundary before any Kitty pane-management logic is added.

## Responsibilities

- ingest DDS-shaped events
- resolve sender IDs to stable participants
- validate authority metadata
- enforce lease holder and epoch
- enforce monotonic per-origin sequence numbers
- reject or ignore invalid events
- emit structured authoritative outcomes

## Decision model

### Commit

Event is accepted when:

- sender maps to a known participant
- lease epoch matches current epoch
- participant matches current lease holder for lease-protected kinds
- origin sequence is strictly increasing
- event ID is not a duplicate
- event does not violate addressed-operation routing policy

### Reject

Event is rejected when:

- sender is unknown
- epoch is stale or future
- sequence is stale or replayed
- sender is not the current lease holder for a lease-protected kind
- addressed operation illegally targets self

### Ignore

Event is ignored when:

- event ID is already known and suppression is configured as ignore

## Input contract

One JSON object per line with:

- `wire` or `wire_raw`
- `meta.event_id`
- `meta.origin_seq`
- `meta.lease_epoch`

## Output contract

One JSON object per line with:

- `decision`
- `reason`
- `wire`
- `meta`
- `state`
