# Milestones

## Stage 0 — Contract and policy scaffold

- DDS envelope schema
- authority sidecar schema
- participant and lease policy files
- runtime policy mirror

## Stage 1 — Coordinator skeleton

- long-lived coordinator event loop
- sender validation
- lease and epoch enforcement
- monotonic sequence enforcement
- duplicate suppression
- authoritative commit/reject/ignore outcomes

## Stage 2 — Kitty pane-mode shell

- fixed two-pane workspace
- peer spawn / close
- single-pane baseline
- focus hints into coordinator
- `ya-layout` shell boundary wired

## Stage 3 — DDS bridge and addressed peer operations

- participant-side DDS bridge
- `reveal_in_peer`
- `cd_peer_here`
- `copy_to_peer`
- `move_to_peer`
- `send_hovered_to_peer`
- `send_selected_to_peer`

## Stage 4 — Neovim adapter

- open selected files in existing server
- reveal current buffer in primary Yazi
- reconcile rename/move/trash/delete against open buffers
