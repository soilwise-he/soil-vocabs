# SoilVoc Feedback Worker

Cloudflare Worker used by the Skosmos feedback page at
`https://soilvoc.wangbeichen.com/soilvoc/en/feedback`.

The Worker receives the existing Skosmos form fields, validates the submission,
and sends one email notification through Cloudflare's `send_email` binding.

## Local Checks

Run from this directory:

```bash
node --test
npx wrangler deploy --dry-run
```

## Deploy

```bash
npx wrangler deploy
```

The production route is configured in `wrangler.jsonc`:

```text
soilvoc.wangbeichen.com/api/feedback
```

## Cloudflare Requirements

- Email Routing must have a verified destination address matching
  `FEEDBACK_TO`.
- The `send_email` binding must allow the same destination address and the
  configured sender address.
- `DEBUG_ERRORS` should stay `false` outside temporary deployment debugging.

Turnstile support is wired in the Worker and Skosmos plugin, but disabled until
a site key and secret are configured.

When changing the Skosmos plugin JavaScript or CSS, also bump the query string
in `skosmos/plugins/soilvoc-definition-source/plugin.json`. The public server
can otherwise let browsers reuse the previous plugin asset for several hours.
