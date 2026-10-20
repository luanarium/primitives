# `napster/modes.py` + `nim/modes/` -- how a client is attached

**Role.** A **mode** is a decision about two independent things: **how the
client finds the sandbox**, and **what stops it reaching anything else.** The
sandbox itself does not change between them.

**In the primitive.** Not lifted -- deployment, not protocol. `BRIEF.md` §5 is
the seal; §1 is the finding that makes the unsealed modes possible.

## The three

| Mode | The client | Finds us by | Sealed by |
|---|---|---|---|
| `byo-wine` | your own Wine prefix | SOCKS for the protocol, WinINet for the webview -- both per-prefix registry | **nothing.** Everything the client *does* comes to us; nothing *prevents* egress |
| `vm-guest` | a client in a Windows VM, or real hardware | the same two settings, applied in the guest from an emitted `.reg` | the VM's own network. A host-only adapter is a stronger and simpler seal than a namespace |
| `museum` | the project's own prefix | SOCKS, plus `/etc/hosts` in a namespace for the webview | a user namespace with **no route out**, asserted on every run by trying |

**Two are intended for release.** The museum is the verification rig: it needs
`unshare`, four relay scripts and a bind-mounted hosts file, so it stays a
shell script run from a checkout rather than something a stranger installs.

## What is sealed, stated plainly

`museum` **guarantees** the client reaches nothing. The others **redirect
every surface the client is known to use**, which is not the same claim: a
client in an unsealed prefix could reach the internet if something in it tried
a path nobody has measured. Saying that out loud on every run is the honest
version.

## Findings encoded here

- **The server runs in the mode's own process**, not behind a subprocess call,
  because a tool install exposes only its own entry point -- its dependencies'
  console scripts are not on the PATH. It also keeps Ctrl-C in the main
  thread, which is what lets the provider shutdown hook fire and the chat
  adapter say goodbye properly.
- **Nothing looks for a checkout.** The exhibit manifests ship inside the
  package, the run directory is under `XDG_RUNTIME_DIR`, and a client is found
  by being told where its prefix is. A mode runs from any directory.
- **Port 80 is tried, then 8080/8088/8008/8800, and the chosen port is
  printed** along with the `nim-client` line that matches it. Port 80 is the
  faithful one -- a client reached *by name* asks for
  `http://www.napster.com/` -- and it needs root; a client pointed at us
  through its own proxy does not care. Returning `None` rather than raising is
  what stops a traceback coming out of a daemon thread.
- **The deployment is memoised**, because building one is **not side-effect
  free**: the collection provider *indexes a directory* when it is loaded, and
  a mode asks for the deployment more than once. Built twice, a large music
  folder is read twice and the first copy is thrown away.
- **A provider name that is not registered is a line of text before the
  banner**, not a traceback out of the middle of one.
- **`warm_if_cold` is not a nicety.** An exhibit served cold is dozens of
  archive requests made while the client is already rendering, and the archive
  rate-limits hard enough that images simply do not arrive.
- **`--chat` and `--web` get no generated `--<domain> NAME` flag.** Chat is the
  one domain an operator picks on purpose, and a `--web NAME` beside the
  `--web-port N` every mode already has is a trap whose error message
  (*"no provider '8080'"*) nobody would thank us for.
- **Every mode takes `--backend` and the per-domain flags**, because a mode is
  a thin composition over the sandbox and a mode that took neither would make
  the two modes intended for release the two a backend cannot be driven from.
- **A mode is a `pyproject.toml`, a `README.md` and one `main()`** that
  composes a `Sandbox`. It declares the sandbox as its only dependency, so
  shipping a mode means shipping that directory and nothing else.
- **Modes are tools; providers are plugins.** `uv tool install` refuses a
  package with no console scripts, so something that fills a capability domain
  goes into the sandbox's own environment with `--with` instead.
- **Several instances is a feature of a mode, not a mode.** It was a fourth
  row in that table for a while, and that was a category error: a mode answers
  how the client finds us and what confines it, and neither answer changes
  because other machines are also running one.

## Lifting it
Lift the two-axis definition -- *how it finds you* × *what confines it* -- and
the honesty about which combination guarantees what. The rest is packaging.
