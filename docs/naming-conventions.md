# Naming Conventions

This document outlines the naming conventions used throughout the project to ensure consistency and maintainability.

## General Guidelines
- Use **kebab-case** for filenames (e.g., `my-component.tsx`).
- Use **PascalCase** for component names and class names (e.g., `MyComponent`).
- Use **camelCase** for variables, functions, and hooks (e.g., `useMyHook`).
- Use **UPPER_SNAKE_CASE** for constants (e.g., `API_BASE_URL`).

## File Naming
- **Components**: Use the component name in PascalCase for the directory and `index.tsx` for the main file (e.g., `MyComponent/index.tsx`).
- **Hooks**: Prefix with `use` and use camelCase (e.g., `useMyHook.ts`).
- **Utilities**: Use descriptive names in camelCase (e.g., `dateUtils.ts`).
- **Pages**: Use PascalCase for directories and `index.tsx` for the main file (e.g., `Dashboard/index.tsx`).
- **Tests**: Use the `.test` suffix (e.g., `App.test.tsx`).

## Component Naming
- Use **PascalCase** for React components (e.g., `MyComponent`).
- Group related components in a directory named after the main component.

## Hook Naming
- Prefix with `use` to indicate a custom hook (e.g., `useNotification`).
- Use camelCase for the hook name.

## Directory Structure
- Group files by feature or domain.
- Use a consistent structure for components, hooks, and utilities.

## Constants
- Use **UPPER_SNAKE_CASE** for constants (e.g., `DEFAULT_TIMEOUT`).
- Place constants in a dedicated file (e.g., `constants.ts`).

## Type Definitions
- Use descriptive names in PascalCase (e.g., `ProcessInstance`).
- Use `.d.ts` for type definition files.

## API Services
- Use camelCase for service functions (e.g., `fetchData`).
- Group related services in a single file (e.g., `api.ts`).

## Testing
- Use the `.test` suffix for test files (e.g., `App.test.tsx`).
- Place test files alongside the files they test or in a dedicated `__tests__` directory.

## Examples
### File Structure
```
src/
  components/
    MyComponent/
      index.tsx
      MyComponent.module.css
  hooks/
    useMyHook.ts
  utils/
    dateUtils.ts
  pages/
    Dashboard/
      index.tsx
  types/
    process.d.ts
```

### Naming Examples
- Component: `MyComponent`
- Hook: `useNotification`
- Utility: `dateUtils.ts`
- Constant: `API_BASE_URL`
- Type: `ProcessInstance`
- Test: `App.test.tsx`

By adhering to these conventions, the project will remain organized and easy to navigate.
