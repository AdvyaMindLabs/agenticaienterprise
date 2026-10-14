# Past tickets and lessons learned (synthetic example)

**TCKT-101 slugify trailing hyphen bug.** A slug helper shipped with leading and trailing hyphens when the input started or ended with punctuation. Lesson: always strip edge hyphens and test inputs with surrounding spaces and symbols.

**TCKT-117 billing client leaked an API key.** A developer hardcoded the billing API key in source and it reached the repository. Lesson: credentials come from environment variables, enforced by the secret scanner.

**TCKT-123 clamp helper accepted inverted bounds.** A clamp utility silently returned wrong values when low was greater than high. Lesson: validate arguments and raise ValueError.
