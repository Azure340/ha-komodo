# HA-Komodo (fork)

This repository is a **fork** of
[`dkarv/ha-komodo`](https://github.com/dkarv/ha-komodo) — a Home Assistant
integration for monitoring [Komodo](https://github.com/moghtech/komodo)
infrastructure.

For upstream installation instructions, configuration, and the full feature
documentation, please refer to the **original repository**:

👉 [https://github.com/dkarv/ha-komodo](https://github.com/dkarv/ha-komodo)

---

## What's different in this fork

This fork is **upstream `dkarv/ha-komodo` v1.3.0-beta1** plus per-container
monitoring and release links.

### Per-container (per-service) stat sensors

Every stack device gains six stat sensors per running service container:

- CPU Usage (%)
- Memory Usage (%)
- Memory Used
- Network Ingress
- Network Egress
- PIDs

Stopped containers report `unknown`.

### Per-server stat sensors

Every server device reports:

- CPU Usage (%)
- CPU Load 1m / 5m / 15m
- Memory Usage (%), Memory Used, Memory Total, Memory Free
- Disk Usage (%), Disk Used, Disk Total, Disk Free
- Network Ingress, Network Egress

### Release links on update entities

Update entities expose a clickable `release_url`. It is taken from the image's
`org.opencontainers.image.source` label when present, and otherwise derived from
the image reference (`ghcr.io` → GitHub releases, Docker Hub → hub page).

Example, in a notification template:

```jinja
{{ state_attr('update.<stack>_<service>_update', 'release_url') }}
```

### Data refresh

The data coordinator refreshes every **60 seconds**.

### Inherited from upstream

- Per-stack on/off switch
- Per-service switch
- Deploy button
- Update entities
- Full resource lists (no 30-item page limit)
- `komodo-api` 2.3.3 (matches Komodo core 2.3.x)

### Sync status

Synced with upstream **v1.3.0-beta1** (2026-09-11).

---

## License

MIT — inherited from the upstream project. See
[`dkarv/ha-komodo/LICENSE.md`](https://github.com/dkarv/ha-komodo/blob/main/LICENSE.md).
