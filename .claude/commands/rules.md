List every file under `.claude/rules/` with its title and top-level headings, so
the user can jump to the right standard quickly.

For each `.md` file in `.claude/rules/` (sorted by name):

1. Print the file path.
2. Print the first `# ` line as the title.
3. Print all `## ` headings as bullets underneath.

Output as a compact markdown list. Do not include file contents — this command
is an index, not a viewer.
