## MODIFIED Requirements

### Requirement: Book metadata retrieval
The system SHALL provide a function to retrieve metadata about each indexed book, including book name and chunk count. The implementation SHALL use paginated reads from the Chroma collection to avoid SQLite variable limits on large collections.

#### Scenario: List books with metadata
- **WHEN** `get_books_metadata()` is called and 3 books are indexed with thousands of total chunks
- **THEN** the result SHALL contain 3 entries, each with `book` (name), `chunk_count` (number of chunks), and `has_source` (whether the source file exists in `SOURCES_DIR`), retrieved via paginated collection reads

#### Scenario: No books indexed
- **WHEN** `get_books_metadata()` is called and the collection is empty
- **THEN** the result SHALL be an empty list

### Requirement: Delete individual book from index
The system SHALL provide a function to remove all chunks belonging to a specific book from both the Chroma vector store (child chunks) and the persistent docstore (parent chunks).

#### Scenario: Delete existing book
- **WHEN** `delete_book("GURPS 4e - Magic.md")` is called and the book exists in the index
- **THEN** all child chunks with metadata `book="GURPS 4e - Magic.md"` SHALL be removed from the Chroma collection, all corresponding parent chunks SHALL be removed from the docstore, and the book SHALL no longer appear in `get_indexed_books()`

#### Scenario: Delete non-existent book
- **WHEN** `delete_book("Nonexistent.md")` is called and no such book is indexed
- **THEN** the function SHALL return without error (idempotent operation)
