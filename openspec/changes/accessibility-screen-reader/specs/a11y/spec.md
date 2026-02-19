## ADDED Requirements

### Requirement: Form controls have programmatic labels
Every form control (`<input>`, `<textarea>`, `<select>`) SHALL have an associated label via `<label for="...">`, wrapping `<label>`, or `aria-labelledby`. Placeholder text alone SHALL NOT be considered a label.

#### Scenario: File upload field announces its purpose
- **WHEN** a screen reader user focuses the file upload input on the Documents page
- **THEN** the screen reader announces "Upload files" (or equivalent label text) along with the accepted file types

#### Scenario: Directory input announces its purpose
- **WHEN** a screen reader user focuses the directory path input on the Documents page
- **THEN** the screen reader announces "Directory path" (or equivalent label text)

#### Scenario: Prompt textarea announces which prompt it edits
- **WHEN** a screen reader user focuses a prompt textarea on the Prompts page
- **THEN** the screen reader announces the prompt name (e.g., "rag" or "multi_question") as the field label

### Requirement: Page heading hierarchy starts at h1
Every page SHALL contain exactly one `<h1>` element identifying the application. Page section titles SHALL use `<h2>`. Heading levels SHALL NOT skip (no h1 → h3 without h2).

#### Scenario: Screen reader heading navigation
- **WHEN** a screen reader user opens the heading list (rotor/elements list) on any page
- **THEN** the list shows an h1 ("CapaRAG") followed by the page-specific h2 ("Chat", "Documents", or "Prompts")

### Requirement: Entity graph modal uses native dialog semantics
The entity graph modal SHALL be implemented as a `<dialog>` element opened via `.showModal()`. The dialog SHALL trap focus while open, close on Escape, and return focus to the trigger button on close.

#### Scenario: Screen reader announces dialog opening
- **WHEN** a screen reader user activates the "Entity Graph" button
- **THEN** the screen reader announces a dialog has opened, reads the dialog title "Entity Graph", and focus moves inside the dialog

#### Scenario: Focus is trapped within dialog
- **WHEN** the entity graph dialog is open and the user presses Tab repeatedly
- **THEN** focus cycles between interactive elements inside the dialog and does not escape to the page behind

#### Scenario: Dialog closes and returns focus
- **WHEN** the user presses Escape or activates the close button inside the entity graph dialog
- **THEN** the dialog closes and focus returns to the "Entity Graph" button that triggered it

### Requirement: Entity graph has accessible text alternative
The entity graph `<canvas>` SHALL be marked `aria-hidden="true"`. The dialog SHALL contain a table summarizing the graph data: entities (name, type, book) and relationships (entity A, relation, entity B). The table SHALL be populated from the same API response used to render the visual graph.

#### Scenario: Screen reader reads entity data
- **WHEN** a screen reader user opens the entity graph dialog
- **THEN** the screen reader can read a table of entities with columns for name, type, and book, and a table of relationships with columns for source entity, relation, and target entity

#### Scenario: Empty graph state
- **WHEN** the API returns no entities for the answer
- **THEN** the dialog displays text "No entities found for this answer" instead of an empty table

### Requirement: Close button has accessible name
Buttons that use iconic content (symbols, SVG, emoji) without visible text SHALL have an `aria-label` describing the action.

#### Scenario: Close button announcement
- **WHEN** a screen reader user focuses the close button in the entity graph dialog
- **THEN** the screen reader announces "Close entity graph" (not "times" or "multiplication sign")

### Requirement: Citation links have descriptive labels
Inline citation links `[N]` SHALL include `aria-label="Citation N"` so screen readers announce "Citation 1" instead of "left bracket, one, right bracket".

#### Scenario: Citation link announcement in answer text
- **WHEN** a screen reader user encounters a citation marker in an answer
- **THEN** the screen reader announces "link, Citation 1" (or the corresponding number)

#### Scenario: Citation link navigates to reference
- **WHEN** a screen reader user activates a citation link
- **THEN** focus moves to the corresponding citation reference block (`#cite-N`)

### Requirement: CSS utility classes for screen reader support
The stylesheet SHALL define `.sr-only` (visually hidden, accessible to screen readers) and `.skip-link` (hidden until focused, then visible). These classes are already referenced in templates.

#### Scenario: Skip link behavior
- **WHEN** a screen reader or keyboard user presses Tab on page load
- **THEN** the first focusable element is the skip link "Skip to main content", which becomes visually visible on focus and navigates to `#main-content` on activation

#### Scenario: sr-only content is read by screen reader
- **WHEN** an element has class `sr-only`
- **THEN** it is not visible on screen but is announced by screen readers
