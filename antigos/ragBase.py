import os
import chromadb
from groq import Groq
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document

# --- CONFIGURAÇÕES GERAIS ---
load_dotenv()
PASTA_DOCUMENTS = "./documentos"
MODELO_IA = "openai/gpt-oss-20b"

# Inicialização dos Clientes
client_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
client_chroma = chromadb.PersistentClient(path="./banco_vetorial")
colecao = client_chroma.get_or_create_collection(name="conhecimento_empresa")

# --- MÓDULO 1: LEITURA DE ARQUIVOS ---
def extrair_texto(caminho_arquivo):
    """Detecta a extensão e retorna o texto do arquivo."""
    extensao = os.path.splitext(caminho_arquivo)[1].lower()
    
    try:
        if extensao == ".pdf":
            leitor = PdfReader(caminho_arquivo)
            return "\n".join([pag.extract_text() for pag in leitor.pages])
            
        elif extensao == ".docx":
            doc = Document(caminho_arquivo)
            return "\n".join([p.text for p in doc.paragraphs])
            
        elif extensao == ".txt":
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                return f.read()
                
    except Exception as e:
        print(f"Erro ao ler {caminho_arquivo}: {e}")
        
    return None

# --- MÓDULO 2: BANCO DE DADOS (INGESTÃO) ---
def processar_arquivos():
    """Lê arquivos da pasta e salva no ChromaDB."""
    print(f"\n--- Processando arquivos em '{PASTA_DOCUMENTS}' ---")
    
    if not os.path.exists(PASTA_DOCUMENTS):
        os.makedirs(PASTA_DOCUMENTS)
        print("Pasta criada. Adicione seus arquivos e tente novamente.")
        return

    arquivos = [f for f in os.listdir(PASTA_DOCUMENTS) if f.endswith(('.txt', '.pdf', '.docx'))]

    for nome_arquivo in arquivos:
        caminho = os.path.join(PASTA_DOCUMENTS, nome_arquivo)
        conteudo = extrair_texto(caminho)
        
        if conteudo:
            print(f"Memorizando: {nome_arquivo}...")
            colecao.upsert(
                documents=[conteudo],
                ids=[nome_arquivo],
                metadatas=[{"origem": nome_arquivo}]
            )
            
    print("--- Ingestão concluída com sucesso! ---")

# --- MÓDULO 3: O RAG ---
def buscar_contexto(pergunta):
    """Busca os trechos mais relevantes no banco."""
    resultados = colecao.query(query_texts=[pergunta], n_results=2)
    
    # Verifica se encontrou algo, senão retorna vazio
    if resultados['documents']:
        return "\n\n".join(resultados['documents'][0])
    return ""

def gerar_resposta(pergunta, contexto):
    """Monta o prompt e chama a API da Groq."""
    prompt = f"""
    Você é um assistente corporativo. Responda usando APENAS o contexto abaixo.

    CONTEXTO:
    {contexto}

    PERGUNTA DO USUÁRIO:
    {pergunta}
    """

    stream = client_groq.chat.completions.create(
        model=MODELO_IA,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        stream=True
    )

    print("🤖 IA: ", end="")
    for chunk in stream:
        print(chunk.choices[0].delta.content or "", end="")
    print("\n")

# --- MÓDULO 4: FLUXO PRINCIPAL ---
def iniciar_chat():
    print("\n--- Chat Iniciado (Digite 'sair' para encerrar) ---")
    while True:
        pergunta = input("\nVocê: ")
        if pergunta.lower() in ["sair", "exit"]:
            break
            
        contexto = buscar_contexto(pergunta)
        gerar_resposta(pergunta, contexto)

if __name__ == "__main__":
    while True:
        print("\n1. Atualizar Memória (Ler Arquivos)")
        print("2. Conversar")
        print("3. Sair")
        
        opcao = input("Escolha: ")
        
        if opcao == "1":
            processar_arquivos()
        elif opcao == "2":
            iniciar_chat()
        elif opcao == "3":
            break