from dotenv import load_dotenv 
load_dotenv() 

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

import io
from docx import Document
import fitz
import easyocr
import re
import spacy

import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise ValueError(
        "A chave da API do OpenAI (OPENAI_API_KEY) não foi encontrada nas variáveis de ambiente. "
        "Verifique o arquivo .env."
    )

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Baixando modelo spaCy 'en_core_web_sm'...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

app = FastAPI(
    title="API de Leitura e Resumo de Currículos",
    description="API para ler currículos em diversos formatos e gerar um resumo do perfil do candidato."
)

reader = easyocr.Reader(['en', 'pt']) 

class ExperienciaDetalhe(BaseModel):
    descricao: str
    inicio: Optional[str] = None
    nome_da_empresa: str
    nome_da_vaga: str
    termino: Optional[str] = None
    e_o_trabalho_atual: bool = False

class FormacaoDetalhe(BaseModel):
    descricao: str
    diploma: str
    instituicao: str
    inicio: Optional[str] = None
    termino: Optional[str] = None
    area: str

class ExtractedInfo(BaseModel):
    nome: str
    email: str
    telefone: str
    experiencia: list[ExperienciaDetalhe]
    formacao: list[FormacaoDetalhe]
    competencias_habilidades: list[str]

class CandidateProfile(BaseModel):
    summary: str
    extracted_info: ExtractedInfo
    file_type: str
    message: Optional[str] = None

async def read_pdf(file_content: bytes) -> str:
    """Extrai texto de um arquivo PDF usando PyMuPDF."""
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler PDF: {e}")

async def read_docx(file_content: bytes) -> str:
    """Extrai texto de um arquivo DOCX usando python-docx."""
    try:
        doc = Document(io.BytesIO(file_content))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler DOCX: {e}")

async def read_image_ocr(file_content: bytes) -> str:
    """Extrai texto de uma imagem usando EasyOCR."""
    try:
        results = reader.readtext(file_content)
        text = " ".join([res[1] for res in results])
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao aplicar OCR: {e}")

async def read_txt(file_content: bytes) -> str:
    """Lê o conteúdo de um arquivo TXT."""
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler TXT: {e}")


async def process_resume_text(full_text: str) -> Dict[str, Any]:
    """
    Processa o texto completo do currículo para extrair informações e gerar um resumo
    utilizando a API do OpenAI para inteligência avançada, alinhado ao DB do Bubble.
    """
    extracted_info_raw = {
        "nome": "Não encontrado",
        "email": "Não encontrado",
        "telefone": "Não encontrado",
        "experiencia": [],
        "formacao": [],
        "competencias_habilidades": [],
    }
    summary = "Não foi possível gerar um resumo detalhado."

    extracted_info_final = {
        "nome": extracted_info_raw["nome"],
        "email": extracted_info_raw["email"],
        "telefone": extracted_info_raw["telefone"],
        "resumo_da_ia": summary,
        "experiencia": [],
        "formacao": [],
        "competencias_habilidades": [],
    }
    
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", full_text)
    if email_match:
        extracted_info_raw["email"] = email_match.group(0)
        extracted_info_final["email"] = email_match.group(0)

    phone_match = re.search(r"(\+?\d{2,3}\s?)?(\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}", full_text)
    if phone_match:
        extracted_info_raw["telefone"] = phone_match.group(0).strip()
        extracted_info_final["telefone"] = phone_match.group(0).strip()

    try:
        prompt_extraction = f"""
        Dado o seguinte texto de currículo, extraia as informações detalhadas e o resumo no formato JSON.
        Se uma informação não for encontrada, use "Não encontrado" para campos de texto, false para booleanos, ou uma lista vazia para arrays.

        Para as datas de Início e Término, use o formato 'YYYY-MM-DD' (preferencialmente) ou 'YYYY-MM'. Se apenas o ano for encontrado, use 'YYYY-01-01'. Se 'Presente' for indicado ou a data de término não for clara, deixe o campo 'termino' como null e 'e_o_trabalho_atual' como true para a experiência em questão.

        Diplomas permitidos para Formação: Bacharelado, Ensino Médio, Ensino Fundamental, Mestrado, Técnico, Doutorado, Pós-graduação, Certificado, Curso Livre, Outro. Use o mais próximo se houver ambiguidade.

        Exemplo de formato JSON esperado:
        {{
            "nome": "Nome Completo do Candidato",
            "resumo_da_ia": "Um parágrafo conciso e envolvente sobre o perfil do candidato, destacando pontos fortes, experiências relevantes e objetivos de carreira.",
            "email": "email.candidato@example.com",
            "telefone": "+55 (11) 98765-4321",
            "experiencia": [
                {{
                    "descricao": "Responsável por desenvolver e manter aplicações web em Python, otimizando performance e integrando APIs de terceiros. Liderou equipe de 3 desenvolvedores em projeto crítico.",
                    "inicio": "2022-03-01",
                    "nome_da_empresa": "Tech Solutions Inc.",
                    "nome_da_vaga": "Desenvolvedor Backend Sênior",
                    "termino": null,
                    "e_o_trabalho_atual": true
                }},
                {{
                    "descricao": "Análise de grandes volumes de dados para gerar insights para o marketing digital. Criação de dashboards interativos em Tableau.",
                    "inicio": "2019-01-01",
                    "nome_da_empresa": "Data Insights Ltda.",
                    "nome_da_vaga": "Analista de Dados Júnior",
                    "termino": "2021-12-31",
                    "e_o_trabalho_atual": false
                }}
            ],
            "formacao": [
                {{
                    "descricao": "Graduação em Ciência da Computação, com foco em algoritmos e estruturas de dados.",
                    "diploma": "Bacharelado",
                    "instituicao": "Universidade Federal XYZ",
                    "inicio": "2014-08-01",
                    "termino": "2018-12-31",
                    "area": "Ciência da Computação"
                }},
                {{
                    "descricao": "Pós-graduação lato sensu com ênfase em redes neurais e aprendizado profundo.",
                    "diploma": "Pós-graduação",
                    "instituicao": "FIAP",
                    "inicio": "2020-02-01",
                    "termino": "2021-06-30",
                    "area": "Inteligência Artificial"
                }}
            ],
            "competencias_habilidades": [
                "Python", "AWS", "Docker", "Machine Learning", "SQL",
                "Comunicação", "Liderança", "Agilidade Scrum", "Análise de Dados"
            ]
        }}

        Texto do Currículo:
        {full_text[:4000]}
        """
        
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "Você é um assistente especialista em análise de currículos e extração de informações para um sistema de recrutamento. Sempre retorne o JSON solicitado de forma completa e válida."},
                {"role": "user", "content": prompt_extraction}
            ],
            temperature=0.1,
            max_tokens=2500,
            response_format={ "type": "json_object" }
        )
        
        openai_output_text = completion.choices[0].message.content.strip()
        
        extracted_llm_data = json.loads(openai_output_text)

        # Atualiza extracted_info_final com os dados do LLM
        extracted_info_final["nome"] = extracted_llm_data.get("nome", extracted_info_final["nome"])
        extracted_info_final["email"] = extracted_llm_data.get("email", extracted_info_final["email"])
        extracted_info_final["telefone"] = extracted_llm_data.get("telefone", extracted_info_final["telefone"])
        extracted_info_final["resumo_da_ia"] = extracted_llm_data.get("resumo_da_ia", summary)
        extracted_info_final["competencias_habilidades"] = extracted_llm_data.get("competencias_habilidades", [])

        # Processar Experiências
        experiencias_ai = extracted_llm_data.get("experiencia", [])
        processed_experiencias = []
        for exp in experiencias_ai:
            processed_experiencias.append({
                "descricao": exp.get("descricao", ""),
                "inicio": exp.get("inicio", None),
                "nome_da_empresa": exp.get("nome_da_empresa", ""),
                "nome_da_vaga": exp.get("nome_da_vaga", ""),
                "termino": exp.get("termino", None),
                "e_o_trabalho_atual": exp.get("e_o_trabalho_atual", False),
            })
        extracted_info_final["experiencia"] = processed_experiencias

        # Processar Formações
        formacoes_ai = extracted_llm_data.get("formacao", [])
        processed_formacoes = []
        valid_diplomas = ["Bacharelado", "Ensino Médio", "Ensino Fundamental", "Mestrado", "Técnico", "Doutorado", "Pós-graduação", "Certificado", "Curso Livre", "Outro"]
        for form in formacoes_ai:
            diploma = form.get("diploma", "Outro")
            if diploma not in valid_diplomas:
                diploma = "Outro"

            processed_formacoes.append({
                "descricao": form.get("descricao", ""),
                "diploma": diploma,
                "instituicao": form.get("instituicao", ""),
                "inicio": form.get("inicio", None),
                "termino": form.get("termino", None),
                "area": form.get("area", ""),
            })
        extracted_info_final["formacao"] = processed_formacoes
        
        summary = extracted_llm_data.get("resumo_da_ia", "Não foi possível gerar um resumo detalhado pela IA.")


    except json.JSONDecodeError as e:
        print(f"Erro: A resposta da OpenAI não é um JSON válido. Detalhes: {e}")
        print(f"Resposta bruta recebida: {openai_output_text[:500]}...")
        summary = "Não foi possível gerar um resumo detalhado. Erro no formato JSON da resposta da IA."
    except openai.APIError as e:
        print(f"Erro na API do OpenAI (status {e.status_code}): {e.message}")
        summary = f"Não foi possível gerar um resumo detalhado. Erro na comunicação com a API da OpenAI: {e.message}."
    except Exception as e:
        print(f"Erro inesperado ao processar com OpenAI: {e}")
        summary = "Não foi possível gerar um resumo detalhado. Ocorreu um erro inesperado na IA."
    
    return {"summary": summary, "extracted_info": extracted_info_final}


@app.post("/upload_resume/", response_model=CandidateProfile)
async def upload_resume(file: UploadFile = File(...)):
    """
    Recebe um arquivo de currículo, lê seu conteúdo e extrai informações para um resumo.
    Suporta PDF, DOCX, Imagem (via OCR) e TXT.
    """
    file_content = await file.read()
    filename = file.filename if file.filename else "unknown"
    file_extension = filename.split(".")[-1].lower()

    full_text = ""
    message = None

    if file_extension == "pdf":
        full_text = await read_pdf(file_content)
    elif file_extension == "docx":
        full_text = await read_docx(file_content)
    elif file_extension in ["png", "jpg", "jpeg", "tiff", "bmp"]:
        full_text = await read_image_ocr(file_content)
        message = "Arquivo de imagem processado com OCR."
    elif file_extension == "txt":
        full_text = await read_txt(file_content)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado: .{file_extension}. Suportados: PDF, DOCX, Imagem (PNG, JPG), TXT."
        )
    
    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Não foi possível extrair texto do arquivo. O currículo pode estar vazio ou muito complexo.")

    processed_data = await process_resume_text(full_text)

    print(openai.api_key)
    return CandidateProfile(
        summary=processed_data["summary"],
        extracted_info=processed_data["extracted_info"],
        file_type=file_extension,
        message=message
    )