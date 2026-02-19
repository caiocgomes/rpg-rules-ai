## MODIFIED Requirements

### Requirement: Document upload interface
The system SHALL provide a page where the user can upload multiple markdown and PDF files simultaneously and trigger batch ingestion. The interface SHALL also accept a local directory path for ingesting all files from that directory. All form controls SHALL have associated labels accessible to screen readers. The file upload input SHALL have a visible `<label>` element. The directory path input SHALL have a visible `<label>` element.

#### Scenario: Upload and ingest multiple files
- **WHEN** the user uploads 3 .md files via the file uploader and clicks the ingest button
- **THEN** the app sends `POST /api/documents/upload` with the files and polls `GET /api/documents/jobs/{id}` for progress

#### Scenario: Ingest from directory path
- **WHEN** the user enters a valid directory path and clicks the ingest button
- **THEN** the app sends `POST /api/documents/ingest` with the directory path

#### Scenario: Screen reader user identifies upload field
- **WHEN** a screen reader user navigates to the upload form
- **THEN** the file input is announced with its label text and accepted file types

#### Scenario: Screen reader user identifies directory field
- **WHEN** a screen reader user navigates to the directory form
- **THEN** the text input is announced with its label text

### Requirement: Aba de edição de prompts
O sistema SHALL exibir uma página "Prompts" na interface onde o usuário pode visualizar e editar os prompts ativos do sistema. Cada textarea de edição SHALL ter uma label programática associada ao nome do prompt via `aria-labelledby`.

#### Scenario: Visualizar prompts atuais
- **WHEN** o usuário navega para a página Prompts
- **THEN** a interface exibe um textarea para cada prompt (RAG e Multi-Question) com o conteúdo atualmente em uso, e indica quais variáveis cada prompt espera receber

#### Scenario: Screen reader user identifies prompt textarea
- **WHEN** a screen reader user focuses a prompt textarea
- **THEN** the screen reader announces the prompt name from the article header as the field label
