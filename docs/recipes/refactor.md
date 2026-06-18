# Refactor Recipe

Recommended mode: `controlled`

## Use When

The structure changes but intended behavior should stay the same.

## Flow

1. Lock existing behavior with checks first.
2. Change one module boundary at a time.
3. Avoid mixing new features into the refactor.
4. Run regression checks and review the diff.

## Done When

Behavior checks still pass and the public behavior is unchanged.
