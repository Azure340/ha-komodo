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

This fork adds per-container resource monitoring on top of the upstream
integration:

- **Per-service container stat sensors** — every stack device gains six
  sensors per service:
  - CPU Usage (%)
  - Memory Usage (%)
  - Memory Used (bytes)
  - Network Ingress (cumulative bytes received)
  - Network Egress (cumulative bytes sent)
  - PIDs (process count)

  Stats are fetched from Komodo's per-stack `listStackServices` API (also
  compatible with the `listAllStackServices` endpoint on newer Komodo builds)
  and computed from the container stats payload.

- **Faster polling** — the data coordinator now refreshes every **60 seconds**
  instead of the upstream 5 minutes.

Everything else — server/stack devices, deploy buttons, per-service switches
and update entities, config flow — matches upstream.

> Note: container stat sensors only report values while a service container is
> running; stopped services report `unknown`.

---

## License

MIT — inherited from the upstream project. See
[`dkarv/ha-komodo/LICENSE.md`](https://github.com/dkarv/ha-komodo/blob/main/LICENSE.md).
