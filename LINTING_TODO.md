# Linting Issues to Address

## Type Annotations
- Add return type annotations to functions in:
  - src/pythmata/core/engine/token.py
  - src/pythmata/core/bpmn/validator.py
  - src/pythmata/core/engine/events/timer.py
  - src/pythmata/api/routes.py
  - src/pythmata/main.py

## Redis Connection Handling
- Fix union-attr errors in:
  - src/pythmata/core/state.py
  - src/pythmata/core/engine/events/timer.py
  - src/pythmata/core/engine/executor.py

## Timer Event Issues
- Fix type issues in src/pythmata/core/engine/events/timer.py:
  - Missing type annotations
  - Datetime operation type issues
  - Redis connection handling

## State Manager Issues
- Fix attribute errors in:
  - src/pythmata/core/engine/events/signal.py
  - src/pythmata/core/engine/events/message.py
  - src/pythmata/core/engine/events/message_boundary.py

## Event System
- Fix coroutine handling in src/pythmata/core/events.py
- Add proper type annotations for message handlers

## General Improvements
- Update poetry.dev-dependencies to poetry.group.dev.dependencies
- Consider adding pre-commit hooks for automated linting
- Add mypy configuration to pyproject.toml for stricter type checking
