# `napster/cli.py`, `clientcli.py`, `configcli.py` -- the three entry points

**Role.** `napster-server` / `napster-sandbox` runs the sandbox; `nim-client`
points a client at it; `nim-config` edits the operator's config.

**In the primitive.** Not lifted. `serve(Backend())` is the whole API; a CLI
is the next tool's own business.

## Findings encoded here

- **Console scripts, not `python -m`.** The project installs with
  `uv tool install` and so does any backend built against it: both ship as
  packages with entry points and run as isolated tools. No virtualenv ritual,
  no global site-packages, and a backend author ships one package rather than
  a checkout plus instructions.
- **`uvx <package>` looks for a script named after the package**, so there is
  one -- which, with the manifests shipping inside the package, makes
  `uvx napster-sandbox` a working museum rather than a server with nothing to
  serve.
- **A query flag answers and exits before anything is set up.**
  `--hosts-line` and `--latency-stage` are queries, not runs -- the harness
  asks the tool for the hosts line so it does not need the package importable
  inside the namespace, and asks for a stage delay so it does not keep a
  second copy of the number.
- **`--capture` without `--socks` is refused**, with the reason: the
  transcript is taken from the proxy the client's traffic passes through, so a
  client talking straight to the protocol port cannot be captured. Writing an
  empty file would be a false promise.
- **The capture warning is printed before recording starts**, not after.
- **Per-domain flags override a bundle**, and an unresolvable name is `return
  2` with the line that fixes it.
- **The MOTD gains three lines pointing at the chat tab** when the chat target
  offers channels -- and **only if the policy is still the default one**, so a
  deployment that brought its own MOTD keeps it.
- **`nim-client show` changes nothing**, and `configure --dry-run` prints the
  commands it would run. Both exist because the thing being edited is somebody
  else's Wine prefix.
- **`nim-client` requires `--nick`**, with the reason in the epilogue: the
  settings are per account and there is no global key to write.
- **`nim-config` has no daemon**, so a staged tree does not survive the
  process and an edit and its `commit` belong in one invocation. The tool says
  `# staged, not written -- add 'commit' to save` on exit if the tree is
  dirty.
- **`commit` refuses a tree that would render wrongly** rather than writing a
  dead link into a client that cannot explain why.
- **A missing optional dependency prints the one line that fixes it.** Reading
  the YAML needs PyYAML; the error says which extra to install, and offers
  moving the file aside as the alternative.

## Lifting it
Nothing to lift. The four habits worth keeping: queries exit before setup,
refuse a flag that cannot do what it promises, warn before recording, and
print the port you actually took.
