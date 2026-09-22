# X Likes Digest

`x-likes-digest` turns newly liked X posts into a content-aware HTML weekly digest for Gmail. It is designed as a lightweight entertainment inbox: discover the increment, group posts by what they contain, and prepare a readable email.

The implementation and its operational rules are documented in [`SKILL.md`](SKILL.md). The supporting command-line tool is [`scripts/x_likes_digest.py`](scripts/x_likes_digest.py).

## What it does

- Reads the account's newly added Likes and keeps an incremental seen-post ledger.
- Groups items by actual content, such as images, videos, text, long-form posts, or external links; empty groups are omitted.
- Produces an HTML digest suitable for Gmail, with original-post links.
- Preserves sensitive items without repeating their text or media in the email body.

For example, a week's digest might contain an **Images** section with two posts, a **Video** section with a duration and “View original post” link, and a **Long-form** section with a short excerpt and source link. This is only an illustrative layout; the sections follow the week's actual Likes.

## Boundaries

- X access is read-only: it does not like, unlike, post, bookmark, or otherwise change X state.
- It does not ingest anything into the Wiki and does not call the acquisition workflow.
- It does not filter out items, add commentary, or embed video thumbnails.
- It does not imply that an email was sent. Delivery is complete only when the Gmail integration returns a message ID.
- Credentials remain managed by the configured OAuth tooling; tokens and secrets are never printed.

The first run establishes an incremental baseline before any later digest can represent new Likes. See [`SKILL.md`](SKILL.md) for the baseline, state, and delivery details.
