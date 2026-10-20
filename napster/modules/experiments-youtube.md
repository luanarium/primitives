# `nim/experiments/youtube/` -- a library provider that is not a collection

**Role.** **Not part of the project.** A `library` provider that answers a
Napster search from YouTube, with real channel names as the nicks. It exists
to find out what the provider seam will take.

**In the primitive.** Not applicable -- but it is the best evidence that the
`Backend`/`Library` seam is the right shape, because it was written against
the seam with no change to the sandbox at all.

| In the client | What is actually happening |
|---|---|
| a search | `yt-dlp --flat-playlist --lazy-playlist --dump-json ytsearch250:<terms>`, read line by line until a deadline |
| a user | the **real** channel name, normalised to a legal Napster nick. Nothing invented |
| a file | the video title as a period Windows path and an `.mp3` |
| a size | estimated from the duration at the encode bitrate |
| a checksum | 32 zeros, which is what OpenNap sent for a file it had not hashed |
| a download | the audio, fetched and encoded on demand, handed over at the modelled line rate |

## Findings that generalise

- **A streaming search is the only usable shape.** `--lazy-playlist` is the
  flag that makes it work: without it yt-dlp extracts the whole result set
  before printing anything -- **8.8s to the first result against 1.1s with
  it**. The deadline then bounds a stream rather than a wait. 110 results in
  6.2 seconds is typical.
- **The client enforces the advertised size, and tolerates a zero checksum.**
  Thirty-two zeros is accepted; a size that does not match is not.
- **The client refuses to share a 32 kHz MP3**, so 44.1 kHz is not arbitrary.
- **Start the fetch in `source_for`, not in `read`.** `source_for` is called
  during the 203/204 exchange, so a fetch started there runs while the client
  acks the download, connects to the data port and sends its `GET`. Started in
  `read`, the data connection sits silent for minutes with the client's own
  timeout running -- measured as **half or more of transfers failing** on a
  constrained link.
- **A failed fetch must drop the connection, not return an empty stream.** An
  empty stream makes a dead video and a slow link identical from the client's
  side. A video that has failed twice is refused during 203/204, which the
  client reports at once.
- **Queue the fetches.** Three concurrent downloads meant three yt-dlp
  processes competing for the same uplink, each making the others slower while
  all three clients counted against their timeouts. Two at a time, and one
  video is fetched once however many readers want it.
- **Call the external tool as a command, not as an import.** The copy in
  `site-packages` is usually years old, and YouTube breaks old extractors
  within months.
- **An emoji in a title hung the client.** This is where the latin-1 lossy
  encode in `wire.py` came from: a title containing `✨` and `🔥` raised
  `UnicodeEncodeError` out of the search handler, which died owing the client
  a 202, and the client sat at *Performing search…* for ever. **Any provider
  can be handed text it did not choose**, which is why the guard belongs at
  the framing layer rather than in each provider.

## Lifting it
Lift the five operational rules -- stream the search, start the fetch early,
fail loudly, queue, and shell out -- for any provider whose data comes from
somewhere slow. They are not YouTube-specific; they are what a remote-backed
`Library` has to do.
