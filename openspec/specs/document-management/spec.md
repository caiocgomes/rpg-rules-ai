## ADDED Requirements

### Requirement: Delete individual book from index
The system SHALL provide a function to remove all chunks belonging to a specific book from the Chroma vector store, identified by the `book` metadata field.

#### Scenario: Delete existing book
- **WHEN** `delete_book("GURPS 4e - Magic.md")` is called and the book exists in the index
- **THEN** all documents with metadata `book="GURPS 4e - Magic.md"` are removed from the Chroma collection, and the book no longer appears in `get_indexed_books()`

#### Scenario: Delete non-existent book
- **WHEN** `delete_book("Nonexistent.md")` is called and no such book is indexed
- **THEN** the function SHALL return without error (idempotent operation)

### Requirement: Book metadata retrieval
The system SHALL provide a function to retrieve metadata about each indexed book, including book name and chunk count.

#### Scenario: List books with metadata
- **WHEN** `get_books_metadata()` is called and 3 books are indexed
- **THEN** the result SHALL contain 3 entries, each with `book` (name), `chunk_count` (number of chunks in the Chroma collection for that book), and `has_source` (whether the source file exists in `SOURCES_DIR`)

#### Scenario: No books indexed
- **WHEN** `get_books_metadata()` is called and the collection is empty
- **THEN** the result SHALL be an empty list
