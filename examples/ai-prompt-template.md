# AI-assisted star categorisation — prompt template

After running `ghstars fetch --out stars.json`, paste the prompt below into your favourite LLM
(Claude, ChatGPT, Gemini, local Llama, whatever) along with the contents of `stars.json`.

The model returns a JSON array in the shape ghstars expects. Save it as `my-categories.json` and run:

```bash
ghstars apply --stars stars.json --categories my-categories.json
```

---

## Prompt

> You are helping me organise my GitHub starred repositories into a small, useful set of lists.
>
> I will paste a JSON array where each item describes one starred repo (`name`, `description`,
> `language`, `topics`, `stars`, `archived`, `fork`).
>
> **Your task:**
> 1. Look at the actual content and propose **between 20 and 32** thematic categories that
>    cover the library. The cap is hard — GitHub allows at most 32 lists per account.
> 2. Each category name must be **≤ 32 characters**, case-insensitively unique, and human-meaningful
>    (a developer should know what's in it from the name alone).
> 3. Two categories are mandatory:
>    - `Archived` — for archived repos (the tool routes them here automatically; just include it).
>    - `Other` — fallback for anything that doesn't match.
> 4. For every other category, write 4–12 regex patterns (Python `re` syntax) that match a
>    repo's `name + " " + description + " " + topics joined`. Patterns are matched **lowercased**,
>    so write them lowercase. Use word boundaries (`\\b...\\b`) where useful.
> 5. Optionally include a `"language"` field that matches a repo's primary language, e.g.
>    `"language": "rust"`. If set, any repo in that language goes to this bucket regardless of patterns.
> 6. Order matters. List narrow categories before broad ones — the first matching category wins.
>    `Archived` short-circuits; `Other` should be last.
> 7. Output only the JSON array, no commentary. Each object looks like:
>
> ```json
> {
>   "name": "string (≤32 chars)",
>   "description": "string (used as the list's description on GitHub)",
>   "patterns": ["regex1", "regex2", "..."],
>   "language": "rust"
> }
> ```
>
> Here are my starred repos:
>
> ```json
> [PASTE CONTENTS OF stars.json HERE]
> ```

---

## Tips

- **Iterate.** Run `ghstars apply --phase plan --categories ai.json --stars stars.json`
  to preview the bucketing. If `Other` is huge, ask the model to refine.
- **Keep it stable.** Once you're happy, commit `my-categories.json` to a dotfiles repo. You can
  re-run categorisation any time as you star new things.
- **Mix and match.** You can hand-edit the file — add patterns, rename buckets, reorder.
- **Validate locally:**
  ```bash
  uv run python -c "
  from pathlib import Path
  from ghstars.categorize import load_categories_json
  from ghstars.validators import validate_category_set
  cats = load_categories_json(Path('my-categories.json'))
  print('Issues:', validate_category_set([{'name': c.name, 'description': c.description, 'patterns': c.patterns} for c in cats]) or 'none')
  "
  ```
