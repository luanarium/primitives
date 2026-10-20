# `napster/clientconfig.py` -- pointing a client at the sandbox

**Role.** Rung 1 of the configuration ladder: **seed the settings the client
was built to read**, rather than intercepting names or patching the binary.

**In the primitive.** Not lifted. `BRIEF.md` §4 is the registry surface and
§5 the desktop seal.

## Two surfaces, two settings

```
HKLM\Software\Napster\<nick>                 protocol (8875/8888) + transfers
    ProxyServer, ProxyPort, ProxyVersion, ProxyTransfers
HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings    the webview
    ProxyEnable, ProxyServer
```

Between them the client needs **no name resolution at all**, because the proxy
routes by destination port.

## Findings encoded here

- **The proxy settings are stored per nick.** Read out of a live prefix:
  `HKLM\Software\Wow6432Node\Napster\CurrentUser = preserve`, then
  `…\Napster\preserve` with `ProxyServer = 127.0.0.1`, `ProxyPort = 1080`,
  `ProxyVersion = 5`, `ProxyTransfers = 1`. **There is no global proxy key**,
  so a seed has to know the nick and the user must sign in as that account --
  anyone else dials `server.napster.com` and fails.
- **On 64-bit Windows a 32-bit app's `HKLM\Software` writes land under
  `Wow6432Node`**, so an emitted `.reg` carries both paths. Inside Wine the
  redirection is handled and one path is enough, but writing both costs
  nothing and makes the file portable between a prefix and a VM.
- **`ProxyUser` and `ProxyPass` are deliberately not written.** A live prefix
  has `ProxyUser = 1` and `ProxyPass = Internal`, which do not read as
  credentials and whose meaning is unknown. **A seed that guesses at them
  would be inventing preservation data.**
- **The download folder must also be in the shared list, or a download is
  invisible to the client for ever.** The client scans its shared folders and
  nothing else, so a file it saved lands somewhere it will never look again:
  refreshing the library does not pick it up however many times it is pressed.
  Observed as 11 `870` share messages at login followed by 11 `102` removals
  after a rescan, and **never a share for either downloaded file**. Sharing
  the download folder is also what the real thing did -- that is how the
  network grew -- so it is on by default.
- **In the `Shared` key the *name* is the folder and the data is a flag**,
  which is why the path appears as a value name and not as a value.
- **The desktop seal is three registry edits and a script.** `WineBrowser`
  `Browsers`/`Mailers` emptied so Wine hands urls to no host program;
  `HKCR\<scheme>\shell\open\command` pointed at the prefix's **own** mshtml
  browser; and `ddeexec` **deleted**, or `ShellExecute` runs the command *and*
  sends IE a DDE message, opening the page twice in one process with the
  second window stacked exactly on the first.
- **The url opener takes a directory lock, and runs under `wscript`.** The
  client calls `ShellExecute` twice for one click, so the handler holds a lock
  for as long as the browser is open -- **a directory, because `CreateFolder`
  throws atomically** and "does it exist then create it" is a race both calls
  win. And `wscript` rather than `cmd` because cmd is a console program and
  Wine gives it a window that then sits beside the page for the whole visit.
  The script is CRLF, because it is a Windows script.
- **A stale lock is cleared when the prefix is configured**, or a crash wedges
  the button behind it.
- **`apply_wine` configures a client; it does not install one.** A prefix with
  no `drive_c` is refused with that distinction stated.

## Lifting it
Lift the registry table, the two "deliberately not written" values, and the
three desktop edits. Each of the last three was a hole that every network-level
assertion passed straight through.
