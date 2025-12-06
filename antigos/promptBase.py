import os
from groq import Groq
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração do Cliente
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Definição dos Prompts (Estratégia Tree of Thoughts) ---
prompt_sistema = """
Você é um especialista em resolução de problemas complexos.
Use a estratégia 'Tree of Thoughts' (Árvore de Pensamentos):

1. Gere 3 soluções possíveis e distintas para o problema do usuário.
2. Para cada solução, analise os prós, contras e a viabilidade.
3. Compare as 3 soluções.
4. Escolha a melhor e explique o porquê.
"""

prompt_usuario = "Como posso fazer uma festa de casamento barata para 200 pessoas?"

# Função auxiliar para enviar o prompt
def consultar_groq(prompt_sistema, prompt_usuario):
    print(f"\n--- Enviando: {prompt_usuario} ---")
    
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0, # Baixa temperatura para ser mais analítico
    )
    
    resposta = completion.choices[0].message.content
    print(f"RESPOSTA DA IA:\n{resposta}")

# Execução do código
if __name__ == "__main__":
    consultar_groq(prompt_sistema, prompt_usuario)