# Memory Agent Skills

## Conversation Summarization

Read all provided conversation messages and produce a compact summary of no more than 400 words.

Use this structure when applicable:

```text
Current objective:
...

Important requirements:
- ...

Completed work:
- ...

Important files and resources:
- ...

Errors and failed attempts:
- ...

Pending work:
- ...

Next action:
...
```

## Important Rules

* Prioritize information required to continue execution.
* Preserve exact filenames, paths, URLs, commands, agent names, and important error messages.
* Summarize long tool outputs instead of copying them.
* Preserve unresolved problems and agent assignments.
* Remove duplicated or obsolete information.
* Treat tool results as more reliable than assistant explanations.
* Never include passwords, API keys, tokens, or other secrets.
* Never exceed 400 words.
* Return only the final summary without additional commentary.


