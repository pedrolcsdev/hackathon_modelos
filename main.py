# ---------------------------
# Cadastro de produtos iniciais
# ---------------------------
def cadastrar_produtos_iniciais():
    # Evita cadastrar duplicado — Chroma usa upsert, então só regrava
    cadastrar_produto(
        nome="Notebook Lenovo Ideapad 3",
        preco="2499.00",
        categoria="notebook",
        modelo="IDP3-2023",
        descricao="Notebook para estudos e uso diário"
    )
    cadastrar_produto(
        nome="Smartphone Samsung Galaxy A14",
        preco="1099.00",
        categoria="smartphone",
        modelo="A14-128",
        descricao="Smartphone custo-benefício com 128GB"
    )
    cadastrar_produto(
        nome="Mouse Sem Fio Compacto",
        preco="59.90",
        categoria="perifericos",
        modelo="MSF-110",
        descricao="Mouse leve e portátil"
    )
    cadastrar_produto(
        nome="Carregador Turbo 20W USB-C",
        preco="79.90",
        categoria="acessorios",
        modelo="TC20W-C",
        descricao="Carregador rápido USB-C de 20W"
    )

# main.py
import warnings
import os
import json
from groq import Groq
from dotenv import load_dotenv
import chromadb
from docx import Document
from pypdf import PdfReader
import sys


warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ---------------------------
# Config
# ---------------------------
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Defina GROQ_API_KEY no seu .env")

client_groq = Groq(api_key=GROQ_API_KEY)
client_chroma = chromadb.PersistentClient(path="./banco_vetorial")
colecao = client_chroma.get_or_create_collection(name="loja_conhecimento")

PASTA_DOCUMENTOS = "./documentos"
MODELO_IA = "openai/gpt-oss-20b"

# ---------------------------
# Estado runtime
# ---------------------------
CARRINHO = []
ESTADO_COMPRA = {"produto_doc": None}

# ---------------------------
# Utils: leitura de arquivos simples
# ---------------------------
def extrair_texto(caminho_arquivo):
    ext = os.path.splitext(caminho_arquivo)[1].lower()
    try:
        if ext == ".pdf":
            leitor = PdfReader(caminho_arquivo)
            textos = []
            for p in leitor.pages:
                try:
                    textos.append(p.extract_text() or "")
                except Exception:
                    textos.append("")
            return "\n".join(textos).strip()
        if ext == ".docx":
            doc = Document(caminho_arquivo)
            return "\n".join([p.text for p in doc.paragraphs]).strip()
        if ext == ".txt":
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"Erro ao ler {caminho_arquivo}: {e}")
    return None

# ---------------------------
# Ingestão simples (cada arquivo -> 1 documento no Chroma)
# ---------------------------
def processar_arquivos():
    print(f"\n--- Processando arquivos em '{PASTA_DOCUMENTOS}' ---")
    if not os.path.exists(PASTA_DOCUMENTOS):
        os.makedirs(PASTA_DOCUMENTOS)
        print("Pasta criada. Adicione seus arquivos (txt/docx/pdf) e rode novamente.")
        return

    arquivos = [f for f in os.listdir(PASTA_DOCUMENTOS) if f.lower().endswith(('.txt', '.pdf', '.docx'))]
    if not arquivos:
        print("Nenhum arquivo encontrado na pasta.")
        return

    for nome in arquivos:
        caminho = os.path.join(PASTA_DOCUMENTOS, nome)
        texto = extrair_texto(caminho)
        if not texto:
            print(f"Pulando {nome} (texto não encontrado).")
            continue

        print(f"Ingerindo '{nome}' ({len(texto)} caracteres)...")
        # Store the whole document as one entry with id = nome
        colecao.upsert(documents=[texto], ids=[nome], metadatas=[{"origem": nome}])
        print(f"  -> '{nome}' armazenado.")
    print("\n--- Ingestão finalizada ---")

# ---------------------------
# RAG lookup: sempre tentamos primeiro
# ---------------------------
def buscar_contexto(pergunta, n_results=3):
    try:
        resultados = colecao.query(query_texts=[pergunta], n_results=n_results)
        docs = resultados.get("documents", [])
        if docs and len(docs[0]) > 0 and any(d.strip() for d in docs[0]):
            # junta os documentos retornados (cada elemento já é um documento inteiro)
            return "\n\n".join([d for d in docs[0] if d and d.strip()])
    except Exception as e:
        print(f"Erro na busca vetorial: {e}")
    return ""

# ---------------------------
# Gerar resposta: RAG primeiro; se não houver contexto -> conversa natural
# ---------------------------
def gerar_resposta(pergunta, historico=None):
    """
    Retorna string com a resposta da IA.
    Estratégia:
    1) busca_contexto -> se encontrou, chama o modelo com instrução para responder SOMENTE com base no contexto.
    2) se não encontrou, chama o modelo com prompt de conversa natural.
    """
    # impedir que o RAG interrompa o fluxo de compra
    if ESTADO_COMPRA.get("fluxo") == "aguardando_quantidade":
        return "Por favor, me informe a quantidade desejada."

    contexto = buscar_contexto(pergunta)
    # 1) Se encontrou contexto, usa RAG (responda apenas com base no contexto)
    if contexto:
        prompt = f"""
Você é um atendente de loja de informática. Responda APENAS usando as informações no CONTEXTO abaixo.
Se a resposta não estiver no contexto, diga exatamente: "Não encontrei essa informação".

CONTEXTO:
{contexto}

PERGUNTA:
{pergunta}
"""
        messages = [{"role": "user", "content": prompt}]
        resp = client_groq.chat.completions.create(
            model=MODELO_IA,
            messages=messages,
            temperature=0.5
        )
        return resp.choices[0].message.content or ""
    # 2) Fallback: conversa natural
    else:
        system = "Você é um assistente amigável e útil para clientes de uma loja de informática. Seja breve e direto."
        msgs = [{"role": "system", "content": system}]
        if historico:
            msgs.extend(historico)
        msgs.append({"role": "user", "content": pergunta})
        resp = client_groq.chat.completions.create(
            model=MODELO_IA,
            messages=msgs,
            temperature=1
        )
        return resp.choices[0].message.content or ""

# ---------------------------
# Produtos & Carrinho (simples, cada produto é um documento no Chroma com id='produto:<nome>')
# ---------------------------
def cadastrar_produto(nome, preco, categoria="", modelo="", descricao=""):
    """
    Cadastra produto como documento textual no Chroma.
    Exemplo do documento:
    PRODUTO:
    Nome: ...
    Preço: ...
    Categoria: ...
    Modelo: ...
    Descrição: ...
    """
    nome_clean = nome.strip()
    doc_text = (
        "PRODUTO:\n"
        f"Nome: {nome_clean}\n"
        f"Preço: {preco}\n"
        f"Categoria: {categoria}\n"
        f"Modelo: {modelo}\n"
        f"Descrição: {descricao}\n"
    )
    prod_id = f"produto::{nome_clean.replace(' ', '_')}"
    colecao.upsert(documents=[doc_text], ids=[prod_id], metadatas=[{"tipo": "produto", "nome": nome_clean}])
    return f"Produto '{nome_clean}' cadastrado com sucesso."

cadastrar_produtos_iniciais()

def listar_produtos():
    """
    Recupera documentos com metadata tipo=produto e formata uma lista.
    """
    try:
        all_data = colecao.get(ids=None)
        docs = all_data.get("documents", [])
        metas = all_data.get("metadatas", [])
        resultados = []
        for d, m in zip(docs, metas):
            if isinstance(m, dict) and m.get("tipo") == "produto":
                # extrai nome e preco do texto
                nome = "Sem nome"
                preco = "Sem preço"
                for linha in d.splitlines():
                    l = linha.strip()
                    if l.lower().startswith("nome:"):
                        nome = l.split(":", 1)[1].strip()
                    if l.lower().startswith("preço:") or l.lower().startswith("preco:"):
                        preco = l.split(":", 1)[1].strip()
                resultados.append(f"- {nome} — R$ {preco}")
        if not resultados:
            return ["Nenhum produto cadastrado."]
        return resultados
    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        return ["Erro ao listar produtos."]

def buscar_produto_por_nome(term):
    """
    Busca inteligente que procura SOMENTE produtos cadastrados.
    Ignora documentos da empresa e PDFs.
    Usa similaridade simples de strings para escolher o melhor produto.
    """
    try:
        # Recupera todos os documentos da coleção
        all_data = colecao.get(ids=None)
        docs = all_data.get("documents", [])
        metas = all_data.get("metadatas", [])
        candidatos = []

        # Filtra apenas documentos que são produtos
        for d, m in zip(docs, metas):
            if isinstance(m, dict) and m.get("tipo") == "produto":
                candidatos.append((m.get("nome", ""), d))

        if not candidatos:
            return []

        # Função de similaridade básica
        def similaridade(a, b):
            a, b = a.lower(), b.lower()
            inter = len(set(a.split()) & set(b.split()))
            return inter

        # Ordena por similaridade
        ordenado = sorted(
            candidatos,
            key=lambda x: similaridade(term, x[0]),
            reverse=True
        )

        # Best match
        melhor_nome, melhor_doc = ordenado[0]
        return [(f"produto::{melhor_nome.replace(' ', '_')}", melhor_doc)]
    except Exception as e:
        print(f"Erro busca produto inteligente: {e}")
        return []

def adicionar_ao_carrinho_por_doc(doc_text, quantidade):
    # extrai nome e preco do doc_text
    nome = "Sem nome"
    preco = 0.0
    for linha in doc_text.splitlines():
        l = linha.strip()
        if l.lower().startswith("nome:"):
            nome = l.split(":",1)[1].strip()
        if l.lower().startswith("preço:") or l.lower().startswith("preco:"):
            try:
                preco = float(l.split(":",1)[1].strip().replace("R$", "").replace(",", "."))
            except:
                preco = 0.0
    subtotal = preco * quantidade
    CARRINHO.append({"nome": nome, "qtd": quantidade, "preco": preco, "subtotal": subtotal})
    return f"{quantidade}x {nome} adicionados ao carrinho (subtotal R$ {subtotal:.2f})."

def mostrar_carrinho_texto():
    if not CARRINHO:
        return "Carrinho vazio."
    s = "🛒 Carrinho:\n"
    total = 0.0
    for i, it in enumerate(CARRINHO, 1):
        s += f"{i}. {it['nome']} — {it['qtd']}x — R$ {it['subtotal']:.2f}\n"
        total += it['subtotal']
    s += f"\nTOTAL: R$ {total:.2f}"
    return s

def finalizar_compra():
    if not CARRINHO:
        print("Carrinho vazio. Nada a finalizar.")
        sys.exit()

    pedido = {"itens": CARRINHO.copy()}
    total = sum(it["subtotal"] for it in CARRINHO)
    pedido["total"] = total
    CARRINHO.clear()

    mensagem = (
        f"Compra finalizada.\n\nPedido: {json.dumps(pedido, ensure_ascii=False, indent=2)}\n\n"
        "Solicitação de compra emitida.\n"
        "Qual forma de pagamento você prefere?\n"
        "- Pix\n- Cartão de crédito/débito\n- Dinheiro\n"
    )

    print(mensagem)
    sys.exit()

# ---------------------------
# Interpretação de comandos simples do usuário (layer de intenções)
# ---------------------------
def tratar_comando_usuario(texto, historico=None):
    texto_l = texto.strip().lower()

    # Correção: impedir que fluxos antigos travem comandos como "finalizar compra"
    if ESTADO_COMPRA.get("fluxo") == "aguardando_quantidade" and texto_l in (
        "finalizar compra", "fechar compra", "confirmar compra"
    ):
        ESTADO_COMPRA["fluxo"] = None
        ESTADO_COMPRA["produto_doc"] = None

    # Saudações simples (evita cair no RAG e retornar "Não encontrei essa informação")
    if texto_l in ("oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
                   "oi bom dia", "ola bom dia", "olá bom dia",
                   "oi boa tarde", "ola boa tarde", "olá boa tarde",
                   "oi boa noite", "ola boa noite", "olá boa noite"):
        return "Olá! Como posso ajudar hoje?"

    # --- NLU via IA: interpretar frases naturais (Opção B) ---
    try:
        prompt_nlu = f"""
Extraia a intenção do usuário para ações de compra.
Retorne SEMPRE um JSON no formato:
{{
  "acao": "comprar" | "adicionar" | "nenhuma",
  "produto": "<nome do produto ou vazio>",
  "quantidade": <numero ou 0>
}}

Frase do usuário: "{texto}"
"""
        resp_nlu = client_groq.chat.completions.create(
            model=MODELO_IA,
            messages=[{"role":"user","content":prompt_nlu}],
            temperature=0
        )
        conteudo = resp_nlu.choices[0].message.content

        # Correção: evitar crash caso o modelo retorne JSON inválido
        try:
            dados = json.loads(conteudo)
        except Exception:
            dados = {"acao": "nenhuma", "produto": "", "quantidade": 0}

        # Se a IA não encontrou intenção de compra, limpamos fluxos pendentes
        if dados.get("acao") == "nenhuma":
            ESTADO_COMPRA["fluxo"] = None
            ESTADO_COMPRA["produto_doc"] = None

        if dados.get("acao") in ("comprar","adicionar"):
            produto_nlu = dados.get("produto","")
            qtd_nlu = int(dados.get("quantidade",0))

            achados = buscar_produto_por_nome(produto_nlu)
            if achados:
                _, doc = achados[0]
                ESTADO_COMPRA["produto_doc"] = doc

                if qtd_nlu > 0:
                    resposta = adicionar_ao_carrinho_por_doc(doc, qtd_nlu)
                    ESTADO_COMPRA["produto_doc"] = None
                    ESTADO_COMPRA["fluxo"] = None
                    return resposta + "\n\n" + mostrar_carrinho_texto() + "\n\n1. Finalizar compra\n2. Adicionar mais itens (digite: listar produtos)"
                else:
                    ESTADO_COMPRA["fluxo"] = "aguardando_quantidade"
                    return "Quantas unidades você gostaria de adicionar?"
    except:
        pass

    # detectar nome informado pelo usuário
    if texto_l.startswith("meu nome e") or texto_l.startswith("meu nome é"):
        nome = texto.split(" ", 3)[-1].strip()
        if historico is not None:
            historico.append({"role": "user", "name": nome})
        return f"Prazer, {nome}! Vou lembrar disso."

    # comandos administrativos
    if texto_l.startswith("cadastrar produto"):
        # formato: cadastrar produto nome=..., preco=..., categoria=..., modelo=..., descricao=...
        try:
            tail = texto[len("cadastrar produto"):].strip()
            # transforma "nome=X, preco=Y" em dict
            pares = [p.strip() for p in tail.split(",") if "=" in p]
            dados = {}
            for p in pares:
                k, v = p.split("=",1)
                dados[k.strip().lower()] = v.strip()
            nome = dados.get("nome")
            preco = dados.get("preco","0")
            categoria = dados.get("categoria","")
            modelo = dados.get("modelo","")
            descricao = dados.get("descricao","")
            return cadastrar_produto(nome, preco, categoria, modelo, descricao)
        except Exception as e:
            return "Formato inválido. Use: cadastrar produto nome=Mouse, preco=59.9, categoria=perifericos"

    if texto_l in ("listar produtos", "mostrar produtos"):
        lista = listar_produtos()
        texto_lista = "\n".join(lista)
        opcoes = (
            "\n\nO que você deseja fazer?\n"
            "1. Escolher um produto digitando: mostrar produto <nome>\n"
            "2. Adicionar um item ao carrinho digitando: comprar <nome>\n"
            "3. Finalizar compra digitando: finalizar compra\n"
        )
        return texto_lista + opcoes

    if texto_l.startswith("mostrar produto") or texto_l.startswith("detalhes produto"):
        # "mostrar produto <termo>"
        term = texto.split(" ", 2)[-1]
        achados = buscar_produto_por_nome(term)
        if not achados:
            return "Não encontrei esse produto."
        # retorna o primeiro achado com texto integral
        _, doc = achados[0]
        # ativar estado de compra automaticamente ao mostrar detalhes
        ESTADO_COMPRA["produto_doc"] = doc
        # adiciona opções de ação ao mostrar detalhes de produto
        opcoes = (
            "\n\nO que você deseja fazer agora?\n"
            "1. Adicionar este item ao carrinho (digite: comprar <nome do produto>)\n"
            "2. Adicionar mais itens (digite: listar produtos)\n"
            "3. Finalizar compra (digite: finalizar compra)\n"
        )
        return doc + opcoes

    # interpretar "adicionar ao carrinho <produto>"
    if texto_l.startswith("adicionar ao carrinho"):
        term = texto_l.replace("adicionar ao carrinho", "").strip()
        if not term and ESTADO_COMPRA.get("produto_doc"):
            ESTADO_COMPRA["fluxo"] = "aguardando_quantidade"
            return "Quantas unidades você deseja adicionar?"
        achados = buscar_produto_por_nome(term)
        if not achados:
            return "Não encontrei esse produto."
        _, doc = achados[0]
        ESTADO_COMPRA["produto_doc"] = doc
        ESTADO_COMPRA["fluxo"] = "aguardando_quantidade"
        return "Quantas unidades você deseja adicionar?"

    if texto_l.startswith("comprar "):
        # "comprar <termo>"
        term = texto.split(" ",1)[1]
        achados = buscar_produto_por_nome(term)
        if not achados:
            return "Não encontrei esse produto."
        # se achou, salva doc no estado global e pergunta quantidade
        _, doc = achados[0]
        ESTADO_COMPRA["produto_doc"] = doc
        ESTADO_COMPRA["fluxo"] = "aguardando_quantidade"
        return "Quantas unidades você gostaria de comprar?"

    # fluxo de quantidade — impede o RAG de interromper
    if ESTADO_COMPRA.get("fluxo") == "aguardando_quantidade":
        import re
        numeros = re.findall(r"\d+", texto_l)
        if numeros:
            qtd = int(numeros[0])
            doc = ESTADO_COMPRA.get("produto_doc")
            if not doc:
                return "Erro interno: produto não encontrado no estado."
            resposta = adicionar_ao_carrinho_por_doc(doc, qtd)
            ESTADO_COMPRA["produto_doc"] = None
            ESTADO_COMPRA["fluxo"] = None
            return resposta + "\n\n" + mostrar_carrinho_texto() + "\n\n1. Finalizar compra\n2. Adicionar mais itens (digite: listar produtos)"
        if texto_l in ("isso mesmo", "sim", "ok", "certo", "certinho"):
            return "Por favor, me informe a quantidade desejada."

    if any(k in texto_l for k in ("carrinho", "itens do carrinho", "ver itens", "mostrar itens", "quais itens")):
        return mostrar_carrinho_texto()

    if texto_l in ("finalizar compra", "fechar compra", "confirmar compra"):
        finalizar_compra()  # imprime direto e encerra o programa
        return ""

    # se não é um comando conhecido, retorna None para o fluxo principal (vai para RAG/natural)
    return None

# ---------------------------
# Chat loop principal
# ---------------------------
def iniciar_chat():
    print("\n--- Chat iniciado (digite 'sair' para encerrar) ---")
    historico = []
    while True:
        pergunta = input("\nVocê: ").strip()
        if pergunta.lower() in ("sair","exit"):
            break

        # 1) tenta interpretar como comando/intent do sistema (cadastro, listar, comprar, etc.)
        cmd = tratar_comando_usuario(pergunta, historico)
        if cmd is not None:
            print("\n🤖 AjudAI:", cmd)
            # se for resposta longa, não adicionar ao historico; se for conversa, pode adicionar
            historico.append({"role":"assistant","content":cmd})
            continue

        # 2) caso não seja comando, vamos ao RAG primeiro e depois fallback de conversa natural
        resposta = gerar_resposta(pergunta, historico)
        # imprime e registra
        print("\n🤖 AjudAI:", resposta)
        historico.append({"role":"assistant","content":resposta})

# ---------------------------
# CLI do utilitário
# ---------------------------
if __name__ == "__main__":
    while True:
        print("\n1. Atualizar Memória (processar documentos em ./documentos)")
        print("2. Conversar")
        print("3. Sair")
        escolha = input("Escolha: ").strip()
        if escolha == "1":
            processar_arquivos()
        elif escolha == "2":
            iniciar_chat()
        elif escolha == "3":
            break
        else:
            print("Opção inválida.")