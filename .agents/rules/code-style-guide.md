---
trigger: always_on
---

- Always need to maintain clean code principles
```
Simplicity (KISS): Avoid unnecessary complexity; always choose the simplest solution that works. 
No Duplication (DRY): Extract common logic into reusable functions or classes to prevent inconsistencies. 
Single Responsibility (SRP): Each function, class, or module should perform only one specific task. 
Meaningful Naming: Use descriptive names for variables and functions (e.g., daysSinceLastUpdate instead of d) to make code self-explanatory. 
Small Functions: Keep methods concise and focused; break large blocks into smaller, testable units. 
Avoid Side Effects: Functions should avoid changing state outside their scope to ensure predictable behavior. 
Readability: Use consistent formatting, indentation, and adhere to language-specific conventions (like PEP 8 for Python). 
YAGNI (You Ain’t Gonna Need It): Only implement functionality that is currently required, avoiding speculative features.
Refactoring: Continuously improve code structure through regular reviews and test-driven development (TDD).
```

- Maintain service layer for making views lightweight.
- Maintain utils for neccessary utility functions.