import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

# ================== CARREGAR VARIÁVEIS DO .env ==================
load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

# ================== CONEXÃO COM MYSQL ==================
conn = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB
)
c = conn.cursor(dictionary=True)

# ================== FUNÇÕES ==================
def adicionar_processo(numero, usuario):
    c.execute(
        "INSERT INTO processos (numero, usuario, status, data_envio, data_fechado) VALUES (%s,%s,%s,%s,%s)",
        (numero, usuario, "Aguardando fechamento", datetime.now(), None)
    )
    conn.commit()

def listar_processos():
    df = pd.read_sql("SELECT * FROM processos", conn)
    return df

def fechar_processos(lista_numeros):
    for numero in lista_numeros:
        c.execute(
            "UPDATE processos SET status='Fechado', data_fechado=%s WHERE numero=%s",
            (datetime.now(), numero)
        )
    conn.commit()

def limpar_historico():
    c.execute("DELETE FROM processos")
    conn.commit()

# ================== LAYOUT ==================
st.set_page_config(page_title="Controle de Processos com Erro", layout="wide")
st.title("Dashboard de Processos com Erro ao Enviar Dados")

# Estilo customizado para as abas
st.markdown("""
    <style>
        .st-aq {
            gap: 0;
        }

        /* Aba normal */
        .stTabs [data-baseweb="tab"] {
            font-size: 18px;
            font-weight: 600;
            color: #ff4b4b;
            padding: 10px 20px;
            border-right: 1px solid #eee;
        }
            
        /* Hover */
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #ff4b4b;
            color: #001969;
            border-right: 1px solid #ff4b4b;
        }
    </style>
""", unsafe_allow_html=True)

aba = st.tabs(["Adicionar processo", "Processos pendentes", "Processos fechados"])


# ================== ABA 1: ADICIONAR PROCESSO ==================
with aba[0]:
    st.subheader("Adicionar processo com erro")

    with st.form("form_adicionar", clear_on_submit=True):
        col1, col2 = st.columns([2, 2])
        with col1:
            numero = st.text_input("Número do processo:")
        with col2:
            usuario = st.text_input("Seu nome:")

        enviar = st.form_submit_button("➕ Enviar processo")
        if enviar:
            if numero and usuario:
                adicionar_processo(numero, usuario)
                st.success(f"Processo {numero} adicionado com sucesso!")
            else:
                st.warning("Preencha todos os campos.")

    # Botão remover processo
    numero_remover = st.text_input("Número do processo para remover:", key="remover")
    if st.button("🗑️ Remover número"):
        if numero_remover:
            c.execute("DELETE FROM processos WHERE numero=%s", (numero_remover,))
            conn.commit()
            st.success(f"Processo {numero_remover} removido!")
        else:
            st.warning("Digite o número do processo que deseja remover.")

# ================== ABA 2: PROCESSOS PENDENTES ==================
with aba[1]:
    st.subheader("Processos pendentes")
    df = listar_processos()
    pendentes = df[df["status"] == "Aguardando fechamento"]

    if not pendentes.empty:
        st.dataframe(pendentes, use_container_width=True)
        lista = "\n".join(pendentes["numero"].tolist())
        st.code(lista, language="text")
        st.info("Copie os números acima para enviar ao ADM.")
    else:
        st.success("Nenhum processo pendente! 🎉")

# ================== ABA 3: GERENCIAMENTO E HISTÓRICO ==================
with aba[2]:
    st.subheader("✅ Processos Fechados")

    # Recarrega df sempre que a aba é exibida
    df = listar_processos()
    pendentes = df[df["status"] == "Aguardando fechamento"]

    # ================== FECHAR PROCESSOS ==================
    # Botão para fechar todos
    fechar_todos = st.button("✅ Marcar todos como fechados")
    if fechar_todos and not pendentes.empty:
        fechar_processos(pendentes["numero"].tolist())
        st.success("Todos os processos foram marcados como fechados!")
        # Atualiza df e pendentes imediatamente
        df = listar_processos()
        pendentes = df[df["status"] == "Aguardando fechamento"]

    if not pendentes.empty:
        st.write("Marque os processos individuais para fechar:")
        for idx, row in pendentes.iterrows():
            col1, col2 = st.columns([3,1])
            with col1:
                st.text(f"{row['numero']} - {row['usuario']}")
            with col2:
                key = f"checkbox_{row['numero']}_{idx}"
                if st.checkbox("", key=key):
                    fechar_processos([row['numero']])
                    st.success(f"Processo {row['numero']} fechado!")
                    # Atualiza df e pendentes imediatamente
                    df = listar_processos()
                    pendentes = df[df["status"] == "Aguardando fechamento"]

    else:
        st.success("Nenhum processo pendente! 🎉")

    # ================== HISTÓRICO DE PROCESSOS FECHADOS ==================
    st.subheader("📊 Histórico de processos (Fechados)")
    fechados_df = df[df["status"] == "Fechado"]

    if not fechados_df.empty:
        # Ordenar do mais recente para o mais antigo
        fechados_df = fechados_df.sort_values(by="data_fechado", ascending=False)
        for col in ["data_envio", "data_fechado"]:
            if col in fechados_df.columns:
                fechados_df[col] = pd.to_datetime(fechados_df[col], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")

        # Área para exibir tabela de fechados
        tabela_area = st.empty()
        tabela_area.dataframe(fechados_df, use_container_width=True)

        # Texto acima do campo copiável
        st.markdown("**Copiar processos fechados**")

        # Campo copiável organizado por usuário
        texto_processos = "Processos Fechados ✅\n"
        for usuario, grupo in fechados_df.groupby("usuario"):
            texto_processos += f"{usuario}:\n"
            for numero in grupo["numero"]:
                texto_processos += f"{numero}\n"
            texto_processos += "\n"

        # Exibe como código
        codigo_area = st.empty()
        codigo_area.code(texto_processos, language="text")

        # Botão limpar histórico fechado
        limpar_fechados = st.button("🗑️ Limpar histórico de processos fechados")
        if limpar_fechados:
            c.execute("DELETE FROM processos WHERE status='Fechado'")
            conn.commit()
            st.success("Histórico de processos fechados limpo!")
            # Atualiza imediatamente tabela e campo copiável
            tabela_area.dataframe(pd.DataFrame(columns=fechados_df.columns), use_container_width=True)
            codigo_area.code("", language="text")

    else:
        st.success("Nenhum processo fechado ainda!")
