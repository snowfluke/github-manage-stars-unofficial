# Proposal: Official API support for Stars Lists

> This document is the case **github-manage-stars-unofficial** would make to GitHub.
> If you work at GitHub and would like us to take this project down, we'll do so — but we'd much rather see an official API land instead.

## tl;dr

Add a small, scoped set of REST endpoints (or GraphQL mutations) so that authenticated users can manage their own **Stars Lists** programmatically:

- `GET    /user/starred/lists` — list my lists
- `POST   /user/starred/lists` — create a list
- `PATCH  /user/starred/lists/{id}` — rename / describe / set private
- `DELETE /user/starred/lists/{id}` — delete a list
- `PUT    /repos/{owner}/{repo}/starred/lists` — set the set of lists this repo belongs to

Same identity, same rate-limits, same audit trail as the rest of the GitHub REST API.

## Why this matters

GitHub's Stars Lists UI is a great organisational primitive — but it is **only** a UI. Today, the only ways to manage lists are:

1. Click each one, one at a time, in a web browser.
2. Reverse-engineer the HTML endpoints that the UI uses (which is what this tool does, reluctantly).

There is no official affordance for any of these legitimate user needs:

- **Bulk-categorising** an existing star library. Users with hundreds or thousands of stars cannot reasonably point-and-click their way through assigning every one.
- **LLM-assisted categorisation.** Users want to dump their stars to JSON, hand them to a model, and apply the suggested grouping. Today the "apply" step has to be done by hand.
- **Backup / restore / migration.** Stars Lists are not in the GitHub Migrations API. If a user wants to move accounts, or just keep a copy of their organisation scheme, they can't.
- **Shareable / forkable list templates.** "Awesome lists"-style curation in a structured, account-attached format would be a great fit for Stars Lists — but only if creators can publish a list definition that consumers can install.
- **Integration with other tooling.** dotfile repos, CLI tools (`gh`), editor plugins, and IDE star explorers could all benefit.

Adding a programmatic API does not change the security or product model of Stars Lists; it just lets users do what they can already do, faster.

## What "minimum viable" would look like

```http
GET /user/starred/lists
Accept: application/vnd.github+json
```
```json
[
  {
    "id": 8067237,
    "name": "API Tooling & OpenAPI",
    "description": "API frameworks, OpenAPI, REST/GraphQL tooling",
    "private": false,
    "slug": "api-tooling-openapi",
    "html_url": "https://github.com/stars/<user>/lists/api-tooling-openapi",
    "repository_count": 6,
    "created_at": "2026-05-17T18:23:01Z",
    "updated_at": "2026-05-17T18:23:01Z"
  }
]
```

```http
POST /user/starred/lists
{
  "name": "AI Agents & Orchestration",
  "description": "Agent frameworks, multi-agent systems",
  "private": false
}
```

```http
PUT /repos/{owner}/{repo}/starred/lists
{
  "list_ids": [8067237, 8067246]
}
```
- Empty array → removes from all lists.
- Non-existent / non-owned IDs → 404.
- Required scope: the new `user:starred` (or reuse the existing `repo`).

## Constraints to keep

The existing UI behaviour observed in 2026:

- 32 lists per account (hard cap).
- 32 characters per list name.
- Names are unique per account, case-insensitive.

These are perfectly reasonable; we just need them documented and enforced server-side with clean error messages.

## What we're committing to

If GitHub ships an API like the above, this project will:

1. Switch its backend to the official API on the next release.
2. Mark the unofficial-UI code path as deprecated and remove it within two minor versions.
3. Hand maintenance over to `gh` / GitHub CLI if the team would prefer Stars Lists support to live there.

Until then, we'll keep this tool gentle: conservative jitter defaults, no parallelism, no scraping beyond the authenticated user's own data, no automation that looks anything like abuse.

## Related discussions

- [community.github.com — Stars Lists API support](https://github.com/orgs/community/discussions/) (search "Stars Lists API")
- [docs.github.com — REST API for starring](https://docs.github.com/en/rest/activity/starring) (documents starring, but not lists)

If you're a GitHub user who wants this: please give those discussions a thumbs up. The squeakier the wheel, the higher this lands on a backlog.
