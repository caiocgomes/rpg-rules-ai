## Why

O sistema hoje é um notebook Colab monolítico que funciona como protótipo. Tudo vive num único arquivo: ingestão de documentos, construção do vector store, definição do grafo, execução de queries. O vector store é in-memory (FAISS sem persistência), os documentos vêm hardcoded do Google Drive, e as credenciais dependem da API do Colab. Não há como deployar isso num servidor, não há interface para usuários finais, e adicionar novos livros exige editar código.

Para virar um produto usável, o sistema precisa de separação de responsabilidades em módulos, persistência do vector store, um pipeline de ingestão de documentos desacoplado da execução de queries, e uma interface (Streamlit) que permita tanto consultar quanto alimentar o sistema com novos livros.

## What Changes

- **BREAKING**: Extrair o código do notebook para uma estrutura de projeto Python com módulos separados (ingestão, retrieval, grafo, API/interface)
- **BREAKING**: Substituir dependências do Colab (google.colab.userdata, drive.mount) por configuração via variáveis de ambiente / `.env`
- Persistir o vector store FAISS em disco (ou migrar para um vector store com persistência nativa)
- Criar pipeline de ingestão que aceita upload de novos documentos markdown e os adiciona ao vector store existente
- Criar frontend Streamlit com duas funcionalidades: chat com o RAG e upload de novos livros
- Estruturar dependências com `pyproject.toml` e gerenciamento via `uv`
- Adicionar configuração para deploy (Dockerfile ou similar)

## Capabilities

### New Capabilities

- `document-ingestion`: Pipeline para upload e indexação de novos documentos no vector store, independente do ciclo de query. Inclui chunking, embedding e persistência.
- `web-interface`: Frontend Streamlit com chat para queries ao RAG e área de upload/gestão de documentos.
- `project-structure`: Estrutura de projeto Python standalone com módulos, configuração por ambiente, gerenciamento de dependências via uv e pyproject.toml.

### Modified Capabilities

_(Nenhuma capability existente com spec; o sistema atual não tem specs definidos.)_

## Impact

- O notebook `Capa_RAG.ipynb` deixa de ser o entrypoint do sistema. Pode ser mantido como referência/documentação, mas o código produtivo migra para módulos Python.
- Dependências mudam: sai google.colab, entra streamlit, python-dotenv, e possivelmente um vector store com persistência nativa (Chroma, por exemplo, que já teve tentativa no notebook).
- Prompts do LangChain Hub (`cgomes/rag`, `gurps_multi_question`) continuam sendo puxados remotamente, mas o código que os invoca muda de localização.
- LangSmith continua como observabilidade, configurado via variáveis de ambiente.
- O vector store precisa de estratégia de persistência: ou FAISS serializado em disco, ou migração para Chroma/outro com persistência built-in.
