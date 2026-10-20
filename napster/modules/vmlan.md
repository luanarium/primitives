# `vmlan/` -- one segment across several hosts

**Role.** **Not built; conventions only.** Put the guests on two or more
machines onto one network as if they shared a switch, with nothing to
administer: no bridge to hand-configure, no VPN to join, no service to
register, no daemon running when the guests are not.

**In the primitive.** Not applicable. It is in this bundle because it is the
other half of the migration: a networking tool, extracted from a preservation
project that needed one.

**[`../NETWORK.md`](../NETWORK.md) is this in full**, together with the
application-layer design above it: the transport decision and why it changed,
the two broadcast modes and where they converge, the seal that is an absent
route, the MTU stack, the guest-side conventions, the privilege split, and the
documented-but-unbuilt answer for crossing a network you do not trust. What
follows is the summary.

## It knows nothing about Napster

It came out of this project, and this project is **one consumer rather than
its owner** -- nothing in `vmlan` imports anything in `nim`, and nothing in
`nim` requires `vmlan`. That separation is the point, and it is the same
separation the next tool should keep.

## Scope: the network, and not the virtual machine

| | |
|---|---|
| **In scope** | discovery, the links between hosts, the segment the guests share, and the configuration of those |
| **Out of scope** | creating, starting, stopping, snapshotting or displaying a VM; installing an OS; anything with a disc in it |
| **The seam** | **a libvirt network, by name, in virt-manager's own list** |

The VMs stay virt-manager's. `vmlan` gives them a network to attach to, so
joining the mesh is one dropdown in a dialog the operator already knows. That
one sentence is the whole design: pick a seam that is already in someone's
hands rather than building a manager around it.

## The conventions worth carrying

- **Layer 2, because the guests should believe they share a switch.** VXLAN
  inside WireGuard: the encrypted transport carries an ethernet segment rather
  than routed packets, so broadcast, ARP and anything that depends on them
  work without translation.
- **`emit` before `apply`, and `apply` needs root while `emit` does not.**
  The operator reads what will be done to their machine first. Same shape as
  `nim-client show` / `configure` and `nim-config` / `commit` -- three tools in
  this project and all three settled on it independently, which is a reason to
  make it a habit.
- **A UCI-style staged config tree**, as `communities.py` uses, for the same
  reason: a small typed tree that both a human and a script edit.
- **A peer only needs declaring if it is not on this segment.** Discovery
  covers the common case; configuration covers the rest.
- **No daemon when the guests are not running.** The thing is a configuration
  step plus kernel state, not a service.

## Lifting it
This is the part of the project most directly on the migration path. Lift the
scope table and the `emit`/`apply` split; re-derive the rest, since it is not
built.
