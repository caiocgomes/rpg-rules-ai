## ADDED Requirements

### Requirement: Chat interface for RAG queries
The system SHALL provide a Streamlit chat interface where the user types a question and receives a structured response from the RAG graph. A resposta MUST display: answer text, list of source books, verbatim citations with source attribution, and "see also" suggestions.

#### Scenario: User asks a question
- **WHEN** the user submits a question via the chat input
- **THEN** the system invokes the LangGraph pipeline (multi_question → retrieve → generate) and displays the structured response with answer, sources, citations, and see_also

#### Scenario: Conversation history
- **WHEN** the user asks a follow-up question in the same session
- **THEN** the system maintains conversation context via LangGraph checkpointer and the response considers prior messages in the thread

### Requirement: Document upload interface
The system SHALL provide a Streamlit page where the user can upload markdown files and trigger ingestion into the vector store.

#### Scenario: Upload and ingest a file
- **WHEN** the user uploads a .md file via the file uploader and clicks the ingest button
- **THEN** the file is passed to the document-ingestion pipeline and a confirmation message is displayed with the number of chunks indexed

#### Scenario: Upload non-markdown file
- **WHEN** the user attempts to upload a file that is not .md
- **THEN** the system SHALL reject the upload and display an error message

### Requirement: List indexed documents
The system SHALL display the list of documents currently indexed in the vector store, extracted from Chroma metadata.

#### Scenario: View indexed documents
- **WHEN** the user navigates to the upload/documents page
- **THEN** a list of distinct `book` metadata values from the Chroma collection is displayed
