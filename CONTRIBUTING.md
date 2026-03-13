# Contributing

Thank you for contributing to Project Scipio.

## Working norms

- Keep changes small and focused.
- Prefer readable code over clever code.
- Preserve the current runtime behavior unless the change explicitly targets that behavior.
- Update `README.md` for any user-visible or architecture-level change.
- Add or update tests when backend logic changes.

## Development checklist

1. Create or update the relevant code.
2. Run `python -m pytest` from the repository root.
3. If you changed ingestion, rules, or replay behavior, document the why in `README.md` using the 5 Ws.
4. Keep screenshots or validation notes when UI behavior changes.

## Pull request guidance

Include:

- what changed
- why it changed
- how it was tested
- any follow-up work or known limitations

## Scope note

Project Scipio is a prototype. Contributions should favor clarity, learning value, and architectural signal.
