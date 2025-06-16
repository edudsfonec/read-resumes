# read-resumes
# API de Análise e Resumo de Currículos

Esta API permite o upload de arquivos de currículo em diversos formatos (PDF, DOCX, TXT, Imagem) e utiliza inteligência artificial (OpenAI GPT) para extrair informações chave do perfil do candidato e gerar um resumo conciso. As informações extraídas são formatadas para serem facilmente integradas com sistemas de gerenciamento de candidatos, como o Bubble.io.

## Funcionalidades

* **Leitura de Múltiplos Formatos**: Suporte para PDF, DOCX, TXT e Imagens (JPG, PNG, TIFF, BMP) via OCR.
* **Extração de Informações Detalhadas**: Nome, e-mail, telefone, lista de experiências profissionais, formação acadêmica e competências/habilidades.
* **Sumarização Inteligente**: Geração de um resumo conciso do perfil do candidato usando a API do OpenAI.
* **Estrutura de Dados Otimizada**: O retorno da API segue um formato JSON pré-definido, alinhado com a estrutura de banco de dados comum em plataformas como o Bubble, facilitando a integração.
* **Validação de Dados**: Uso de Pydantic para validação de entrada e saída dos dados da API.

## Tecnologias Utilizadas

* **FastAPI**: Framework web de alta performance para construção da API.
* **OpenAI API**: Para funcionalidades avançadas de processamento de linguagem natural (extração e sumarização).
* **python-docx**: Para leitura de arquivos DOCX.
* **PyMuPDF (fitz)**: Para leitura de arquivos PDF.
* **EasyOCR**: Para extração de texto de imagens (OCR).
* **spaCy**: Para algumas operações de processamento de texto (embora a maior parte da inteligência seja do OpenAI).
* **python-dotenv**: Para carregar variáveis de ambiente de forma segura em ambiente de desenvolvimento.
* **Pydantic**: Para definição e validação de modelos de dados.

## Pré-requisitos

Antes de iniciar, certifique-se de ter o Python 3.9+ instalado em seu sistema.

### Chave da API do OpenAI

Você precisará de uma chave de API válida da OpenAI. Se você não possui uma, pode gerá-la em: [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)

## Configuração do Projeto

Siga os passos abaixo para configurar e executar a API localmente:

1.  **Clone o Repositório (se aplicável):**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <nome_da_pasta_do_projeto>
    ```

2.  **Crie um Ambiente Virtual (Recomendado):**
    É uma boa prática isolar as dependências do projeto.
    ```bash
    python -m venv venv
    ```

3.  **Ative o Ambiente Virtual:**
    * **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Instale as Dependências:**
    ```bash
    pip install fastapi uvicorn python-docx pymupdf easyocr spacy openai python-dotenv
    ```

5.  **Baixe o Modelo spaCy (Necessário para OCR e NLP básico):**
    ```bash
    python -m spacy download en_core_web_sm
    ```

6.  **Configure sua Chave da API OpenAI:**
    Crie um arquivo chamado **`.env`** na **raiz do seu projeto** (na mesma pasta de `main.py`). Dentro deste arquivo, adicione sua chave da API da seguinte forma:

    ```
    OPENAI_API_KEY="sua_chave_completa_e_valida_do_openai_aqui"
    ```
    **Lembre-se:** Substitua `"sua_chave_completa_e_valida_do_openai_aqui"` pela sua chave real. Este arquivo `.env` não deve ser versionado (adicione-o ao `.gitignore`).

## Executando a API Localmente

Após a configuração, você pode iniciar a API usando Uvicorn:

```bash
uvicorn main:app --reload
