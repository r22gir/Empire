# SocialForge and MarketForge status

SocialForge is the owner of every online account (social, marketplace, email, directories, Canva, and domain email) for each business. The account hub is `GET /api/v1/socialforge/accounts/hub`.

Nothing auto-publishes. A post stays a draft, or is marked `held`, until the founder turns on that account's `auto-publish` toggle and the publisher is not paused.

OAuth providers stay at `needs_keys` until the env keys below are set. eBay, Amazon, and the other non-Etsy marketplaces report `needs_keys` or `not_connected`. They do not return a success URL.

## What is real

- Account hub for Workroom and WoodCraft, with status, owner (`socialforge`), and last sync.
- Fernet vault (`EMPIRE_VAULT_KEY`). It refuses to start without a valid key. Plaintext `social_accounts.access_token` values are sealed and the column is replaced with `vault:<id>`. API responses do not include tokens.
- Founder PIN (`X-Founder-Pin`) for migration, OAuth start, auto-publish, and the pause switch.
- Meta (Facebook and Instagram Graph), Pinterest, and LinkedIn authorize URLs and token refresh requests. The callback seals the token.
- Publisher tick for Facebook and Instagram, with retry (3 attempts), per-post status, and a pause switch.
- Etsy Open API v3: PKCE connect, shop token sealed in the vault, listing create forced to `draft`, listings and orders read with GET.

## Register these redirect URIs

Public base defaults to `https://studio.empirebox.store`. Override with `EMPIRE_PUBLIC_BASE_URL`. The URI registered at each provider must match that base plus the path.

| Provider | Redirect URI |
|----------|----------------|
| Meta (Facebook Login, used for Facebook and Instagram) | `https://studio.empirebox.store/api/v1/socialforge/oauth/meta/callback` |
| Pinterest | `https://studio.empirebox.store/api/v1/socialforge/oauth/pinterest/callback` |
| LinkedIn | `https://studio.empirebox.store/api/v1/socialforge/oauth/linkedin/callback` |
| Etsy | `https://studio.empirebox.store/api/v1/marketforge/oauth/etsy/callback` |

## Env keys

| Key | Used for |
|-----|----------|
| `EMPIRE_VAULT_KEY` | Fernet key. The vault will not start without it. |
| `EMPIRE_PUBLIC_BASE_URL` | Optional. Defaults to `https://studio.empirebox.store`. |
| `META_APP_ID` | Meta app id |
| `META_APP_SECRET` | Meta app secret |
| `PINTEREST_APP_ID` | Pinterest app id |
| `PINTEREST_APP_SECRET` | Pinterest app secret |
| `LINKEDIN_CLIENT_ID` | LinkedIn client id |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn client secret |
| `ETSY_CLIENT_ID` | Etsy keystring. PKCE does not use a client secret. |
| `FOUNDER_PIN` | Founder gate for connect, vault migration, and publish controls |

Meta scopes requested: `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`, `business_management`.

Pinterest scopes: `boards:read`, `pins:read`, `pins:write`.

LinkedIn scopes: `openid`, `profile`, `w_member_social`.

Etsy scopes: `listings_r`, `listings_w`, `transactions_r`, `shops_r`.

## Still not connected

TikTok, X, Google Business, Houzz, Thumbtack, Yelp, Nextdoor, Canva, domain email, business email, eBay, Amazon, Facebook Marketplace, and Craigslist are listed in the hub and stay `not_connected` or `needs_keys`. There is no publisher for them and no fake OAuth success.
