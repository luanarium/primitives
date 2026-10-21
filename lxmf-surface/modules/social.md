# `social` -- posts, comments and reactions, as a set question

**Role.** The social half: a feed, a thread, and a reaction, built so that two
instances holding the same events agree without consulting a clock.

**In the primitive.** Lifted, as §8.

## What it provides

`post`, `comment`, `react`, `retract`, `delete`, and the readers `posts`,
`comments`, `thread`, `reactions`, `feeds`.

## What it expects

A store, and an identity to sign with. Nothing else -- every reader is a pure
function of the stored set.

## Findings encoded here

- **These kinds belong to the core, not to a plugin.** A kind is a claim about
  how the whole surface treats a payload. The cost of the alternative was
  concrete rather than philosophical: a plugin manifest had to account for a
  closed list of capability domains exactly once, so adding a tenth domain
  invalidated every existing plugin and gained nothing a core module did not
  already give.
- **A feed is a topic, so nothing creates one.** `post` is the default feed and
  is **cross-talk by design**: a Mastodon adapter, a chat adapter and a web view
  are three windows onto one feed rather than three feeds. `post/<name>` exists
  the moment somebody writes into it.
- **A comment rides its post's topic**, so one subscription carries a feed and
  its replies, and a comment cannot land in a feed its post is not in. The cost
  is stated rather than hidden: a busy feed's subscribers receive its comments
  too, which is right for a few instances and would want revisiting at a
  hundred.
- **Reactions are an OR-Set, and that replaced latest-wins.** An add is an
  event, its own id is the add's unique tag, a removal names the add it cancels,
  and the set is every add no removal *from the same author* names. Why
  latest-wins failed: `created` is a second and reacting then changing your mind
  happens well inside one, so a tie was the normal case; breaking it by id makes
  every instance agree on an answer as likely to be the *first* reaction as the
  last. Two instances that received the same pair in opposite orders disagreed
  and kept disagreeing, because arrival order is fixed once stored.
- **A removal that arrives before its add still removes**, because resolution
  asks the whole set rather than replaying it. Nothing resurrects.
- **Changing a reaction is a removal and an add, done by the verb.** The data
  type stays honest and the convenience lives in the verb -- so if another
  client ever leaves two adds standing, both are shown, because that is what the
  set says.
- **A reaction is `async`, not ephemeral.** An ephemeral one would vanish from
  the store and leave a count nobody could recompute.
- **Posts and comments were already convergent.** A tombstone names its target
  and is checked against that target's author, which is a pure set operation.
  Only latest-wins needed a clock it could not have.
- **Deletion is a tombstone, never a removal**, and only the author's own
  counts: a target somebody else wrote is not theirs to retract. A superseded
  post stays readable, which is the difference between an edit and a loss.
- **A thread is flat and in reading order.** A chain of ids is stored, not a
  tree. The walk decides *which* comments belong to the thread and not their
  order -- returning them in walk order puts every direct reply before any
  reply-to-a-reply, which is a shape rather than a conversation.
- **Arrival order is used for display and nothing else.** Two instances can show
  a pair of same-second posts in different orders, which is cosmetic where the
  same ambiguity in a reaction was not.
- **Every listing prints twelve characters of a sixty-four character id and
  every verb accepts a unique prefix**, because a command that printed an id it
  would then refuse could not be used from its own output. Exact wins over
  prefix; an ambiguous prefix is refused and says how many matched.
- **A plugin that publishes speaks as the operator.** An instance has one
  identity, so every event a plugin produces is stamped `via` with its name **by
  the core**, never taken from the content -- so one cannot claim to be another
  or to be nobody.

## Lifting it

Take §8 whole. The OR-Set resolution is the part not to re-derive; the verb
behaviour around it is a convenience you can change.
