# Brand assets for the integration tile

Home Assistant pulls integration logos at runtime from
[`home-assistant/brands`](https://github.com/home-assistant/brands), keyed
on the integration's domain. There is no manifest field that overrides
this — it's the same path for every integration, core or custom.

For the integration card to show the **iAquaLink** logo (instead of the
generic puzzle icon), these four files need to land in `home-assistant/brands`
under `custom_integrations/zodiac_iaqualink/`:

| File         | Source                                          | Size      |
|--------------|--------------------------------------------------|-----------|
| `icon.png`   | https://brands.home-assistant.io/iaqualink/icon.png    | 256×256   |
| `icon@2x.png`| https://brands.home-assistant.io/iaqualink/icon@2x.png | 512×512   |
| `logo.png`   | https://brands.home-assistant.io/iaqualink/logo.png    | 1077×256  |
| `logo@2x.png`| https://brands.home-assistant.io/iaqualink/logo@2x.png | 2157×512  |

Copies of these files are bundled in this folder ready to drop into a
brands PR.

## How to submit

1. Fork <https://github.com/home-assistant/brands>.
2. Create the directory `custom_integrations/zodiac_iaqualink/`.
3. Copy the four PNG files from this folder into it.
4. Open a PR titled `Add Zodiac iAquaLink Heat Pump (custom_integrations/zodiac_iaqualink)`
   describing it as a HACS custom integration that talks to the iAquaLink
   cloud, reusing the existing iAquaLink logo since it shares the same
   underlying brand.
5. Once merged, restart Home Assistant — the logo will appear on the
   integration tile and on every entity's device page.
