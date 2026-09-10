# CER-AI public search discovery

## Scope of this change

The existing `/corneal-ectasia-risk-assessment` product page now explains the product category, AI-assisted Pentacam image reading, the separate canonical rule-based assessment engine, the workflow, and public worked examples. New editorial blocks have English and Turkish versions controlled by the existing public language selector. Existing branding, title, H1, clinical evidence boundaries and application access remain unchanged.

The public page links to existing synthetic educational cases. It does not claim a real-patient Pentacam demo or live analysis is available. Publish real examination images only after the separate de-identification, rights/permission and clinical-content review is complete.

No clinical rule, threshold, score, extraction source, report generator, archive or authentication code is changed. No additional tracking script or patient-data analytics is introduced. Existing search/training crawler permissions are preserved; permitting search crawling is not a reason to silently change model-training preferences.

## Verification in this repository

- `tests/test_public_search_discovery.py`: actual public-route responses, clear AI boundaries, matched language blocks, public links, canonical address, crawler rule specificity and staging no-index behavior.
- `tests/test_public_site.py`: existing public-site contracts, unchanged.
- `.github/workflows/public-discovery.yml`: public tests, complete application regression suite, desktop/phone browser language-switch and overflow checks, and read-only HTTP audits. It does not deploy anything or use production credentials.
- `scripts/check_public_discovery.py`: GETs only the homepage, product page, robots.txt and sitemap.xml on the explicit production or staging host. It never calls analysis or patient-report endpoints. The output identifies HTTP observations separately from unverified search indexing. Verification-token values are not logged.

A failed network probe is not proof of site downtime or de-indexing. Browser checks run against the changed static page; route/canonical checks run through the actual public route owner. Production HTTP checks examine the currently deployed production revision, not an unpromoted feature branch. Staging HTTP checks examine the current staging revision at the time of each run. Network-audit steps report failures without hiding them as successful indexing.

## Promotion gates

1. Review the PR diff: public HTML, tests, audit utility, documentation and test workflow only.
2. Require the public discovery and existing regression tests to pass. Review desktop and phone English/Turkish outputs.
3. Promote to the designated staging branch. Confirm the Railway deployment revision and SUCCESS status. Do not accept unrelated pending Railway environment changes.
4. Obtain explicit owner approval before promoting to production. Staging must remain non-indexable.
5. After production promotion, run `python scripts/check_public_discovery.py --environment production` and inspect the actual deployed page, canonical, robots and sitemap.

## Search ownership and indexing: separate, outstanding work

During the initial infrastructure audit, the production service did not list `CERAI_GOOGLE_SITE_VERIFICATION` or `CERAI_BING_SITE_VERIFICATION` as configured environment variables. This does not establish that the site lacks verification: DNS or verification-file methods may already have been used. No authenticated Search Console or Bing Webmaster Tools inspection or sitemap submission has been performed by this change.

Authorized owner access is required to check the existing properties and avoid duplicate setup. Use the actual tokens supplied by Google/Bing if the supported HTML-meta method is selected; never invent tokens or request the owner's password. The public-site route owner already supports these two variable names. Do not expose private API keys.

For Google Search Console and Bing Webmaster Tools, verify the correct `cer-ai.com` property, inspect the homepage and product URL, confirm Google's selected canonical where available, and submit the production sitemap `https://cer-ai.com/sitemap.xml` if it has not already been submitted. Record the submission acknowledgement separately from actual indexing. Request indexing only for the approved production public pages. Do not submit staging, archives, reports or application endpoints.

## Discovery is not a guaranteed recommendation

Allowing search crawlers, publishing useful information, software structured data or an llms.txt file does not guarantee indexing, ranking or inclusion in an AI answer. This release makes no claim that CER-AI is already listed by ChatGPT, Google, Bing, Claude or Perplexity. Distinguish HTTP accessibility, crawler permissions, confirmed indexing, answer citations and user visits.

Useful official starting points:
- Google AI search guidance: https://developers.google.com/search/docs/appearance/ai-features
- Google URL Inspection: https://support.google.com/webmasters/answer/9012289
- OpenAI crawler roles: https://platform.openai.com/docs/bots
- Bing Webmaster Tools: https://www.bing.com/webmasters/

Robots directives are crawler guidance, not access control. Protect clinical records through the existing application security boundary; do not rely on robots.txt to conceal patient information.
