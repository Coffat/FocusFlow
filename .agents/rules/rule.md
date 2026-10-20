# Focus Flow — Coding Rules

> These rules are **inviolable**. AI agents must follow them without exception.

---

## Backend Rules (Python)

### General

- Python 3.12+
- Type hints on all function signatures
- Docstrings on all public functions
- `async/await` for all I/O operations
- No bare `except:` — always specify exception type
- Use `logging` module — no `print()` in production code
- Use `orjson` for JSON serialization where performance matters

### Naming

- **Files/Folders**: `snake_case` (e.g., `emotion_memory.py`)
- **Classes**: `PascalCase` (e.g., `EmotionService`)
- **Functions/Variables**: `snake_case` (e.g., `get_emotion_hint`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- **Env vars**: `SCREAMING_SNAKE_CASE` (e.g., `EMOTION_ENABLED`)

### Patterns

- Factory for creating provider instances
- Singleton for service instances
- Pydantic for all data models and config
- `asyncio.Semaphore` for concurrency limits
- `tenacity` for retry logic

### Testing

- Tests in `tests/` mirroring source structure
- Use `pytest` with async support
- Mock external APIs — no real API calls in tests
- Each test must be independent and deterministic

---

## 🅰 Frontend Rules (Angular v21+)

### TypeScript

- Use `const` by default — never `var`
- Use `async/await` — never `.then()/.catch()`
- Never use `any`, `null`, `undefined`, `unknown` — always declare explicit types
- Exported object shapes use `interface`; use `type` for literal and discriminated unions that `interface` cannot represent
- Unused parameters: prefix with `_` (e.g., `_event`)
- Never use `private`, `readonly`
- Every component must have `ngOnInit`
- `@Input()` and `@Output()` must use correct decorators
- `subscribe()` must include `next`, `error`, `complete` callbacks
- Never leave unused imports or variables
- Avoid duplicate code
- Do not write `: void` — it is the default
- Boolean `true` default: write property name only, not `="true"`
- Naming: Component/Service → `PascalCase`, Variable/Function/Module → `camelCase`, Constant → `SCREAMING_SNAKE_CASE`, Files/Folders → `kebab-case`
- Function names describe action: `getUsers()` not `fetchFromApi()`

### Angular

- Use `@for` / `@if` — never `*ngFor` / `*ngIf` (Angular v21+)
- Service must be `class` with `@Injectable`, inject via `constructor`
- Subscribe must unsubscribe — prevent memory leaks (use `takeUntilDestroyed()` or `DestroyRef`)

### HTML

- Use **PrimeNG** for UI components (button, table, dialog, etc.)
- Class names use `-` only — never `_` or `__`

### SCSS

- Each file: **exactly 1 `@media`** block and **1 `::ng-deep`** block, grouped in one place
- Never use `!important` — use `::ng-deep` for specificity
- Never use `font-family`
- Minimize `:host` usage
- Always responsive design
- **Colors**: Use semantic CSS variables set at app startup from 1 file, example `light.json` (e.g., `var(--primary)`, `var(--on-surface)`). And 1 file, example `palette.json` holds only swatch tokens (`red-100`, `blue-2400`); semantic and component mappings live in `light.json`. Do not reference palette swatch keys (`--grey-100`) in SCSS. **Never hard-code colors**.
- No color fallbacks — always use CSS variable directly
- Use `rgba(var(--abc-rgb), 0.1)` — never mix transparent colors manually
- Iterator color: `color: var(--iterator-color)`

### Translations

- All display text must use translation variables
- No inline strings for user-facing text
