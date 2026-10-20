# The network layer: between instances, and one segment across hosts

**Designed, not built.** This is the part of the source project that is *not*
a Napster idea, and therefore the part most directly on the path into a
standalone networking tool. It is two designs with shared conventions and
deliberately separate implementations:

| | |
|---|---|
| **Between instances** | several machines each running a sandbox and a client, sharing what their operators put in their own collections. Searches run across all of them, chat reaches across all of them, and a transfer is a direct connection between two of them. Application layer |
| **`vmlan`** | put two or more machines' guests onto one network as if they shared a switch, with nothing to administer. Layer 2, knows nothing about Napster, and already lives in its own folder depending on nothing in the preservation project |

The conventions are the same across both: multicast says a node exists, a peer
may be written down instead, a group needs a secret, announcements carry
nothing private, and `emit` precedes `apply`. **The implementations are not,
and should not be.** One discovers application instances and opens control
links to them; the other discovers hosts and joins their guests at layer 2.
Neither imports the other, neither requires the other, and a machine may run
either alone.

---

## 1. Two framing decisions, both reached by trying the other thing first

**This is a feature of a mode, not a mode.** It was a fourth row in the mode
table for a while and that was a category error: a mode answers *how does the
consumer find us* and *what confines it*, and neither answer changes because
other machines are also running one. So any mode can turn it on. Start with
the cheapest pair of real nodes available -- two prefixes on two machines --
because the VM case brings a second and separable problem, which is §5 below.

**No rendezvous, index exchange or control traffic over a chat network.**
Discovering peers, or being told about them, covers the same ground with no
server in it. The first version of this design made IRC the meeting point,
with a channel carrying presence and an introduction and a DCC CHAT carrying
control traffic. It was dropped for three reasons, in the order they matter:

- **It is a dependency on somebody else's infrastructure** for a feature whose
  entire point is that two machines on a desk can find each other. Either the
  operator runs a daemon for a job multicast does with no daemon at all, or
  the peers meet on a public network, which drags in rate limits, bans, and
  the question of whether machine chatter is welcome there.
- **The control traffic never fitted.** An ircd gives roughly a line a second
  with a small burst and a 512-byte line, and a flood kill for exceeding it.
  An index is thousands of rows. So the design needed a direct link *anyway*,
  negotiated through the channel -- which means the channel was only ever a
  phone book, and a phone book is a config line.
- **It never solved the trust problem it appeared to.** Registered accounts
  are the one real identity IRC offers and they exist on services networks
  only; elsewhere a nick is not an identity and cannot be made into one. A
  group secret is both simpler and stronger than the thing it replaces.

---

## 2. Three layers, each doing the one thing it is good for

```
directory          who exists      mDNS on the segment, or a peer written down
control link       index sync,     a direct TCP line protocol between instances,
                   chat, get         nothing in the middle
data               the bytes       the consumer's own 1999 peer protocol, both ends
```

**The layering is the point, not the mechanisms.** Swapping the top row is how
the same feature works on a segment and across a routed network. The bottom
row is unchanged in both cases, and it is code that has to exist anyway.

---

## 3. Discovery is the only part that varies, and it is a provider

"How does an instance learn that another exists, and at what address" is the
only question whose answer differs between a segment and a routed network.
Everything above it -- what the index looks like, how it stays current, how
bytes move, how chat crosses -- is identical.

| Directory | How a peer is found | When |
|---|---|---|
| **mDNS / DNS-SD** | multicast on the segment, zero configuration | the LAN case, and the default |
| **configured** | written down: a host, a port, a group | a routed network, a VPN, a host multicast cannot reach, and **the first thing to reach for when something is wrong** |

**The data path never varies.** A directory's whole job is to produce
`(name, address, port, version)` and say when a peer arrives or leaves.
Nothing below that line knows which one found the peer, which is what makes
the second one a configuration file rather than a second implementation.

### On a segment there is nothing to run

**DNS-SD over mDNS** (RFC 6762/6763), service type `_<app>._tcp.local`, which
is what every printer and media box on the network already does. A mature
pure-Python implementation exists and needs no system daemon, though it
coexists with one: both want UDP 5353, and sharing it is the normal case.

The TXT record is the whole announcement, and it is deliberately thin:

```
_<app>._tcp.local   <instance>._<app>._tcp.local   <address>:<control port>
  txt: v=1 nick=<the identity this node presents>
       idx=<index version, a monotonic counter>
       link=<the link speed this node declares>   files=<count>
```

- **`idx` is why this works without a reliable channel.** Multicast is not
  reliable, so **the thing announced must be a version, never a change**. A
  peer that misses a packet notices at the next announcement because the
  number moved, and asks for what it is missing. Broadcasting the deltas
  themselves means one dropped datagram and two indexes that disagree for
  ever, with nothing in the design able to detect it.
- **Nothing about the content is in the record.** Not titles, not paths, not
  the operator. A multicast announcement goes to everything on the segment,
  including whatever else is on the café wifi, so the record says a node
  exists and what to dial. The index is answered over the control link, to a
  peer that has authenticated.
- **The announcement is opt-in per run.** A tool that multicasts by default
  announces the operator onto whatever network they happen to be on, and the
  networks a laptop joins are mostly unknown ones.
- DNS-SD also hands over two solved problems: **instance name conflicts** are
  resolved by the spec, and a node that leaves sends a goodbye record, so
  **departure is an event rather than a timeout**.

### Off the segment, a peer is written down

A list, needing no protocol at all: a host, a port, and the group secret.
Written-down peers and discovered ones are the same thing once the directory
has them, and a node may have both. **A configured peer is dialled rather than
waited for**, which is also what makes it the honest answer to "why can these
two not see each other": take multicast out of the question and find out.

---

## 4. The control link

### Index push, not search fan-out

The first design had a query fan out to every peer with a **deadline** rather
than a quorum, because a terminator has to arrive. Pushing the indexes instead
is better on every axis that matters:

- **The terminator becomes immediate and complete.** A query runs against a
  local merge of every node's index, so there is no slowest peer, no partial
  result and no deadline to tune. The pacing that makes the experience right
  stays *ours* to control rather than being hostage to a peer that is
  swapping.
- **It costs almost nothing at this scale.** A row is a couple of hundred
  bytes of metadata; a personal collection of 50,000 files is about 10 MB. For
  a handful of nodes, holding everyone's index is cheaper than the connection
  churn of fanning out on every keystroke.
- **It makes the per-user listing work.** A request for one user's whole list
  is answered from memory rather than with a round trip.

### The wire

```
HELLO <proto> <nick> <link> <idx>     both ways, once, on connect
INDEX <since>                         "I have up to this version"
ROW <md5> <size> <bitrate> <freq> <secs> :<filename>
...
DONE <idx>                            now you have this version
BYE                                   a clean departure
```

Line-oriented, one token per field, **the filename last because it is the only
field that can contain spaces**. `INDEX 0` is a full transfer, and a node
whose index is rewritten wholesale bumps far enough that everyone asks for 0
again.

**An index has exactly one writer**: the node whose files they are. No merge
conflict to resolve and no conflict policy to design.

### Chat rides the same link

Chat lines are tiny and rare compared with an index, so they need no second
connection and no negotiation:

```
SAY <channel> :<text>            to everyone in the group
JOIN <channel> / PART <channel>  so the rosters agree
WHO <channel>                    on connect, to populate one
```

Four conventions, three of them existing rules applied here:

- **The consumer learns nothing.** A remote user appears as an ordinary member
  of an ordinary channel, through the same remote-session mechanism that puts
  chat-network users in the roster today. Every byte the consumer receives
  stays inside its own 2001 message set.
- **A nick is attributed to the node that owns it.** No merging, no rewriting,
  and **no fabricated persona ever speaks**: invented users populate search
  results and must never appear to type.
- **No history.** A node relays what it hears while it is up and keeps
  nothing. Nothing to design, nothing to leak, and a late-joining node sees
  what happens next, which is what a 1999 chat room did anyway.
- **The chat-network option remains available and remains optional**, selected
  by configuration rather than implied, and the two are not exclusive: the
  adapter was already written to hold several networks at once.

---

## 5. The data path: the instances are the peers

**This is the load-bearing decision of the whole design**, and the two
readings of "direct" are not the same thing:

| | Who dials whom | What it needs |
|---|---|---|
| consumer to consumer | A's client dials B's client's data port | B's client must serve a request it was never told about (unmeasured), B's port must be reachable, and both ends need the firewalled push path |
| **instance to instance** | A's client dials A's node on loopback; A's node dials B's node; B's node reads the file | one TCP connection between the two machines, and the peer-protocol code that has to exist anyway |

The second is the one to build, and it is still direct in the sense that
matters: **one connection between the two nodes, no third party.** What it
buys:

- **The unmeasured client behaviour stops mattering.** B's client is never
  asked to serve anybody.
- **The push path disappears.** No firewalled-peer negotiation, no injected
  upload request. Those exist because a *client* may be unreachable; two
  instances on a LAN are both reachable.
- **The unit of sharing is the instance's collection, not the client's share
  table** -- which the project is already built for, because the collection
  folder is deliberately disjoint from what the client offers. A node shares
  what its operator put there, and the client's own downloads stay nobody
  else's business.
- **The address problem dissolves.** The download ack to A's client carries
  A's own node's data port on loopback, which is the address it is most
  certain of. Nothing has to report an address learned off a socket.

What crosses for a transfer is therefore not a protocol message but a fetch:

```
GET <md5> :<filename>    ->   SIZE <bytes> then the bytes, or NO <reason>
```

**The filename and the checksum cross verbatim** -- no prefixing, no path
normalisation -- because they are index keys owned by the far end and the
downloading client checks both.

**A filename is an index key, never a path.** A remote fetch resolves through
the index or is refused. It is attacker-controlled text and the obvious attack
is `..\`.

---

## 6. Trust, with no accounts anywhere in sight

With the chat network out of the control plane there are no accounts at all:
anything on the segment can multicast, answer, and ask for an index. So the
honest minimum is a **shared secret per group**, given once to each node and
proven on the control link before an index is served or a chat line accepted.

- **Without one the feature refuses to start** rather than serving openly. **A
  LAN is not an allowlist.**
- **It is the same string for every node in a group**, which is what makes it
  a group. A deliberate choice of weak-but-comprehensible over
  strong-but-ceremonial: it is a passphrase an operator can read down the
  phone to the person in the other building, and the threat it is sized for is
  somebody else on the café wifi, not a determined attacker on the path.
- **Carry it as a proof, never as the string.** A nonce from the listener,
  HMAC back. A passphrase replayed in cleartext on a shared segment is a
  passphrase anyone on it has.
- **Discovery is public, membership is not.** The record says a node exists
  and what to dial; the secret is checked on the connection rather than
  announced with it.

---

## 7. `vmlan`: one segment across several hosts, and nothing else

### Scope: the network, and not the virtual machine

**It does not manage VMs.** No launching, no window, no ISO handling, no disc
swapping, no guest lifecycle of any kind. An earlier draft had all of that and
it was the wrong tool growing a second job.

What it does instead is **interoperate with the thing people already use**:
the operator sets their VMs up in virt-manager the way they would anyway, and
the tool provides a network for those VMs to attach to. One dropdown in a
dialog they already know, rather than a second way to run a virtual machine.

| | |
|---|---|
| **In scope** | discovery, the links between hosts, the segment the guests share, and the configuration of those |
| **Out of scope** | creating, starting, stopping, snapshotting or displaying a VM; installing an OS; anything with a disc in it |
| **The seam** | **a libvirt network, by name, in virt-manager's own list** |

That last line is the whole design: **pick a seam that is already in
somebody's hands rather than building a manager around it.**

### The transport changed when the command line stopped being ours

An earlier draft chose QEMU's `-netdev l2tpv3`, on the grounds that it needs
no root and leaves no host interface behind. **That choice depended on
launching QEMU ourselves**, which the scope decision above removes:
virt-manager owns the domain XML, and injecting a netdev through
`<qemu:commandline>` fights the tool being interoperated with.

So the transport is **VXLAN on a host bridge** (RFC 7348): ethernet over UDP,
in the kernel, supported everywhere, and the one shape libvirt attaches a
guest to without being asked twice.

```
br-mesh      a bridge with no uplink
  vxlan0     id 42, dstport 4789 -- the other hosts
  vnet0..n   whatever libvirt attached
```

- **On one segment there is no per-peer state at all.** A VXLAN interface with
  a multicast group floods and learns like a switch, so two hosts on the same
  LAN need nothing told to them. This is the case the project is for and the
  case with the least in it.
- **Off the segment, a peer is one FDB entry.**
  `bridge fdb append 00:00:00:00:00:00 dev vxlan0 dst <host>`, one per remote
  host, which is exactly what the configured peer list is for. **Discovery and
  configuration feed the same table.**
- **A link is point to point and a group is the full mesh**, with no elected
  hub and nothing to fail over.
- **VXLAN carries no authentication**, which is worth saying plainly rather
  than implying the group secret covers it. The secret authenticates the
  application's own control links; a VXLAN segment is protected by the network
  it crosses and by the VNI being obscure, which is enough for a LAN and is
  **not** enough for the open internet. So the scope is a network the operator
  trusts, and **the useful thing is to say that in the output** rather than
  imply otherwise.

### The bridge with no uplink is the mesh and the seal at once

This is the part worth noticing. A guest attached to a bridge that has a VXLAN
port and **no gateway** can reach the other guests, can reach its own host,
and can reach nothing else -- **a seal achieved by there being no route rather
than by a firewall denying one.**

- **The guest needs one NIC, not two.** The host has an address on the mesh,
  so a client in a guest reaches its own machine's server over the same
  segment it reaches the other guests over. No second host-only adapter to set
  up.
- **Host IP forwarding must be off for that interface**, or the seal leaks
  through the host's own uplink. It is the one assertion this design has to
  make, and it is checkable in a line.

### Guest-side conventions, for a period Windows guest

- **A NIC model the guest already has a driver for.** Windows XP has drivers
  for `e1000` and `rtl8139` and **none for virtio-net** without the virtio-win
  disk, so the default advice is `e1000`. Picking virtio in virt-manager and
  getting a guest with no network is the first thing that will happen to
  somebody otherwise.
- **No DHCP, and nothing to run one.** A mesh with two hosts has nowhere
  obvious to put a DHCP server and two obvious places to put a conflict.
  Windows assigns itself a `169.254.0.0/16` address when no server answers,
  which XP does by default and which is exactly right here; the host takes a
  stable link-local address derived from its node name. Static addresses are
  the alternative where predictability matters more than
  nothing-to-configure.
- **mDNS works over link-local**, so discovery needs nothing special on an
  APIPA segment.

### Privilege, and how it is crossed

Creating a bridge, a VXLAN interface or an FDB entry needs `CAP_NET_ADMIN`;
defining a libvirt network needs a system connection. **Neither is something a
user-level tool install should quietly acquire.** So the split is on privilege,
and the crossing uses the same convention three other tools in this project
arrived at independently -- **emit, then apply**:

```
vmlan show      what is configured, and what is actually up. Needs nothing
vmlan emit      the ip/bridge commands and the libvirt network XML, to stdout
sudo vmlan apply   the same, applied, with a dry run available
vmlan watch     discovery only: find peers, print what their FDB entries would be
```

An operator who wants to read what will touch their network before it does
can; one who does not can `sudo` once. **What there is not is a daemon that
acquires root at install time**, or one running when the guests are not.

### Configuration

UCI's shape, because it is a worn-in answer to "a flat file a human edits and
a program also writes", and because anyone who has configured an OpenWrt box
already knows it. Same verbs -- `get`, `set`, `add`, `del`, `show`, `commit`
-- and **writes stage until committed**.

```
config node 'this'
    option name 'loft'   option group 'housemates'   option secret '...'
    option vni  '42'     option uplink 'eth0'

config peer 'studio'
    option host '10.0.0.42'
```

- **One file under `$XDG_CONFIG_HOME`**, not `/etc`. This is a user install.
- **Every runtime flag has a config key, and the flag wins.** A tool
  configurable only by file is awkward to script; one configurable only by
  flags has nothing to read when it starts at boot.

---

## 8. Out of scope, documented: VXLAN inside WireGuard

**Not being built.** This section exists so the answer is on the shelf rather
than rediscovered: it is what somebody would need to know to carry this across
a network they do not trust, and the mechanics are not obvious.

**WireGuard is layer 3 and cannot be bridged.** Its interface is
`ARPHRD_NONE`, not `ARPHRD_ETHER`: no MAC address, no ARP, no concept of an
ethernet frame. There is no TAP mode, and `ip link set wg0 master br0` is
refused because enslaving requires an ethernet device. Checkable on any
machine: `cat /sys/class/net/*/type` prints `1` for an ethernet device and
`65534` for a point-to-point tunnel of this class. A VMware host-only adapter
reads 1 and is bridgeable; a tunnel of the WireGuard kind reads 65534 and is
not. WireGuard also routes by **cryptokey routing** -- each peer owns a set of
`AllowedIPs` and an outgoing packet goes to *exactly one* peer, the most
specific match. **One packet cannot be sent to several peers.**

**The VXLAN device is a real ethernet device**, which is the whole reason for
putting it on top: `ARPHRD_ETHER`, a MAC, enslavable to a bridge, and it
encapsulates **the entire inner ethernet frame** including its header, so
non-IP traffic rides too. The VXLAN endpoints are then the hosts' WireGuard
addresses rather than their public ones, so the UDP it generates is routed out
through `wg0` and encrypted on the way.

| | |
|---|---|
| Layer 2? | yes, at the VXLAN layer. One bridge, one broadcast domain, guests on different hosts in it |
| Ethernet frames? | yes, whole frames with their headers, so ARP and non-IP protocols cross |
| UDP? | yes, that is what VXLAN is. **Pass `dstport 4789`**: Linux defaults to 8472, its own pre-IANA number, and says so. Two hosts configured by different hands, one of them explicit, do not meet |
| Broadcast? | yes, by **head-end replication**, not by multicast |

**Broadcast works, but not the way it works on a segment.** VXLAN has two
modes for broadcast, unknown-unicast and multicast traffic:

- `group 239.x.x.x` -- flood via IP multicast. Zero per-peer state, and **this
  cannot work inside WireGuard**: a multicast packet would have to reach every
  peer, and cryptokey routing sends it to one. This is the on-segment mode and
  it stays on the segment.
- **one all-zeros FDB entry per peer.** The kernel then replicates that
  traffic as unicast to each listed peer, which is ordinary traffic as far as
  WireGuard is concerned. **This is the mode a tunnel would need, and it is
  already the mode specified for a peer that is off the segment** -- the one
  piece of good news here, because the two cases converge and nothing has to
  be built differently in advance. A written-down peer and a tunnelled peer
  are the same FDB entry pointing at a different address.

That replication is the cost: every broadcast frame is sent once per peer and
encrypted once per peer. For a handful of machines it is nothing, and what it
buys is the point: **IP multicast survives the crossing**, so mDNS discovery
works across such a mesh when it would not work over WireGuard alone.

**The MTU is the thing that will actually bite.** The overhead stacks and
nothing in the path reports it:

```
1500   the physical link
1420   wg0        -- 80 bytes (outer IP + UDP + WireGuard's 32), wg-quick's own default
1370   the guest  -- 50 more (outer IP 20 + UDP 8 + VXLAN 8 + inner ethernet 14)
```

A guest left at 1500 sends segments that cannot be delivered, and path MTU
discovery does not rescue it: the ICMP that would tell it is as likely as not
filtered, which is **a silent stall rather than an error**. Windows XP's MTU is
a per-interface registry value, which is a miserable thing to talk somebody
through, so fix it on **our** side: **clamp the TCP MSS on the bridge**
(`--clamp-mss-to-pmtu`, or a fixed 1330). Everything this project carries over
that segment is TCP, so clamping covers it. The alternative, where the
switches allow it, is to raise the physical MTU to 1600 and leave the guest at
1500, which is the datacenter answer and needs hardware that agrees.

---

## 9. Findings that are facts about the protocols, not about the design

Kept because they outlive the design that turned them up.

**Napster and DCC solved the NAT problem identically, with the same
sentinel.** A download ack carrying `<port>` 0 and a passive DCC offer
carrying `port` 0 are the same statement, and the fallback each triggers is
the mirror of the other: the side that cannot be dialled asks the other side
to dial it. Anyone building the consumer-to-consumer path later gets that for
free rather than inventing it.

**They disagree on byte order, and both encode an IP as a decimal integer.**
127.0.0.1 is `16777343` on the Napster wire -- little-endian, pinned by
capture -- and `2130706433` in a DCC offer, which is network order. Anything
bridging the two needs both conversions and **must never assume**.

**Never relay bulk data over an ircd.** Not as a fallback, not as a test. It
is abuse, it earns a ban, and it is the one thing that would make a
preservation project a nuisance to the networks it is a museum of. Nothing in
the current design goes near an ircd, which is the most reliable way to keep
that rule.

**A lead worth chasing: the `napster:` URL handler.** The client registers
itself as a Windows URL protocol handler and is invoked as
`napster.exe -p <url>`; the grammar is the last significant undocumented
client surface. If it addresses a nick and a filename then **chat is already a
sharing mechanism for humans**: someone pastes a link into a channel, it
reaches the chat tab as an ordinary public message, and clicking it hands the
client a download to ask the server about. No protocol extension at all. It is
cheaply testable with what exists: feed candidate forms to `-p` inside the
sealed prefix and watch the transcript, which sees every byte. The handler is
already pointed at a wrapper of our own for another button, so the invocation
path is understood end to end.

---

## 10. The conventions, as a checklist

The fourteen the design states before anyone writes it. Numbers 1 to 8 and 11
to 14 are the application layer; the rest hold for both.

1. **No server in the middle.** Discovery is multicast or a written-down peer;
   the control link is a direct TCP connection; the bytes are the existing
   peer protocol. Nothing needs a tracker, a relay or an account anywhere.
2. **Discovery is a provider; everything above it is not.** One interface, two
   implementations, and no code below that line knows which one found the
   peer. Anything reaching deeper than the interface is a second
   implementation wearing the word "fallback".
3. **Announce a version, never a change.** A dropped announcement costs a
   round trip; a dropped *delta* costs two indexes that disagree permanently
   with nothing able to notice.
4. **An index has exactly one writer.** No merge to resolve, no conflict
   policy to design.
5. **The instances are the peers.** A node serves bytes off its own disk, no
   consumer is ever involved in anybody else's upload, and the shared unit is
   the instance's collection rather than the consumer's own share table.
6. **A filename is an index key, never a path.** Attacker-controlled text,
   crossing verbatim because the far end checks it.
7. **Discovery is public, membership is not.** The record carries nothing
   private; the secret is proven on the connection as a challenge and
   response. With no secret configured the feature refuses to start.
8. **Multicasting is opt-in per run.**
9. **Emit before apply, and apply is the only thing needing privilege.** No
   daemon acquires root at install time, and none runs when the guests do not.
10. **Every runtime flag has a config key, and the flag wins.**
11. **Transcode or precompute at index time, never in the stream.** A result
    row carries the size and checksum of the exact bytes that will be sent and
    the consumer checks both, so a transfer is a pipe and nothing else.
12. **Pace what there is to pace.** One greeting per peer on connect and no
    periodic chatter of our own beyond what the discovery protocol does.
13. **The consumer learns none of it.** Every message it receives stays inside
    its own 2001 message set. A remote user is an ordinary channel member, a
    remote file an ordinary result row. This is the extension most tempted to
    break that rule.
14. **No history, anywhere.** Nothing to design, nothing to leak.

---

## 11. What exists, and what the glue actually is

Three of the four application-layer pieces are already built in the source
project:

- **Remote identity.** The chat bridge already registers a remote user as a
  session with `remote=True` and an `origin`, written for chat-network users;
  the mechanism is the same for a user on another instance. A result row has
  to be attributable to a session that exists, and it already is. **Give that
  session a share dict and it is a peer with files.**
- **The seams.** The library's `search` and the rendezvous provider's
  `resolve` are the two interception points, and `proxied=True` is the relay
  case already named.
- **The peer protocol on both sides**, which has to exist anyway for the local
  collection -- so a relay is two peer connections plumbed together rather
  than new protocol work.

The glue is four pieces, three of them small:

| | |
|---|---|
| **`PeerDirectory`** | the federation provider. Arrivals, departures, `(name, address, port, version)`. Two implementations. **The only piece that differs between a segment and a routed network** |
| **The control link** | one TCP connection per peer, greeting then `INDEX <since>`, re-pulled when an announced version moves |
| **`FederatedLibrary`** | wraps the local library and merges pulled indexes into its search and browse answers, attributing each row to the node that holds it. A local merge, so the terminator arrives at once |
| **`FederatedRendezvous`** | turns a hit on a remote node into our own data port, and fetches through that node behind it |

**Nothing in the consumer-facing message set changes, which is the test of
whether an extension is in scope.** And fabricated owners stay on local rows:
a remote row is attributed to the identity that node's operator chose, because
the merge happens locally and **misattributing who has what is the one thing
the illusion must not do.**

`vmlan` itself is unbuilt: conventions, the scope table, the transport
decision and the privilege split, all above.

## What it buys

A 2001 client ends up on a topology that did not exist when it was written:
several machines with no server between them, a directory that is a multicast
packet, chat with nothing in the middle, and a data plane that is still
exactly the peer protocol of 1999. The client is unmodified throughout and
cannot tell. **That is the preservation claim in its strongest form: not an
emulation of the network, but the original client on a network reassembled
from parts that need nobody's permission to run.**
