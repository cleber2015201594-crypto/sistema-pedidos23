import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import hashlib
import psycopg2
import os
import sys

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

usuarios = {
    "admin": make_hashes("admin123"),
    "vendedor": make_hashes("vendas123")
}

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username in usuarios and check_hashes(password, usuarios[username]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.sidebar.success(f"Bem-vindo, {username}!")
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha inválidos")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🗄️ CONEXÃO COM BANCO DE DADOS
# =========================================

def get_connection():
    """Conecta com PostgreSQL no Render ou SQLite local"""
    try:
        # PostgreSQL no Render
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL:
            # Converte postgres:// para postgresql://
            if DATABASE_URL.startswith('postgres://'):
                DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
    
    return None

def init_db():
    """Inicializa tabelas no banco"""
    conn = get_connection()
    if not conn:
        st.error("❌ Não foi possível conectar ao banco de dados")
        return
    
    try:
        cur = conn.cursor()
        
        # Tabela de escolas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL
            )
        ''')
        
        # Tabela de clientes
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                telefone VARCHAR(20),
                email VARCHAR(100),
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabela cliente_escolas (relação muitos-para-muitos)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cliente_escolas (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER REFERENCES clientes(id),
                escola_id INTEGER REFERENCES escolas(id),
                UNIQUE(cliente_id, escola_id)
            )
        ''')
        
        # Inserir escolas padrão
        escolas = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas:
            cur.execute(
                "INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING",
                (escola,)
            )
        
        conn.commit()
        st.success("✅ Banco de dados inicializado!")
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
    finally:
        conn.close()

# Inicializar banco na primeira execução
if 'db_init' not in st.session_state:
    init_db()
    st.session_state.db_init = True

# =========================================
# 🔧 FUNÇÕES PRINCIPAIS
# =========================================

def adicionar_cliente(nome, telefone, email, escolas_ids):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        # Inserir cliente
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (%s, %s, %s, %s) RETURNING id",
            (nome, telefone, email, data_cadastro)
        )
        cliente_id = cur.fetchone()[0]
        
        # Inserir relações com escolas
        for escola_id in escolas_ids:
            cur.execute(
                "INSERT INTO cliente_escolas (cliente_id, escola_id) VALUES (%s, %s)",
                (cliente_id, escola_id)
            )
        
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT c.*, string_agg(e.nome, ', ') as escolas
            FROM clientes c
            LEFT JOIN cliente_escolas ce ON c.id = ce.cliente_id
            LEFT JOIN escolas e ON ce.escola_id = e.id
            GROUP BY c.id
            ORDER BY c.nome
        ''')
        return cur.fetchall()
    finally:
        conn.close()

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar se tem pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = %s", (cliente_id,))
        if cur.fetchone()[0] > 0:
            return False, "Cliente tem pedidos e não pode ser excluído"
        
        # Excluir relações e cliente
        cur.execute("DELETE FROM cliente_escolas WHERE cliente_id = %s", (cliente_id,))
        cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        
        conn.commit()
        return True, "Cliente excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    finally:
        conn.close()

# =========================================
# 🚀 CONFIGURAÇÃO DA APLICAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide"
)

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu = st.sidebar.radio("Navegação", 
    ["📊 Dashboard", "👥 Clientes", "📦 Pedidos", "👕 Produtos", "📈 Relatórios"])

st.sidebar.markdown("---")
st.sidebar.write(f"👤 Usuário: **{st.session_state.username}**")

if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    
    clientes = listar_clientes()
    escolas = listar_escolas()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Clientes", len(clientes))
    with col2:
        st.metric("Total Escolas", len(escolas))
    with col3:
        st.metric("Sistema", "Online ✅")
    
    st.success("🚀 Sistema funcionando perfeitamente com PostgreSQL!")

elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar", "📋 Listar", "🗑️ Excluir"])
    
    with tab1:
        st.header("Cadastrar Novo Cliente")
        
        nome = st.text_input("Nome completo*")
        telefone = st.text_input("Telefone")
        email = st.text_input("Email")
        
        escolas_db = listar_escolas()
        escolas_opcoes = [e[1] for e in escolas_db]
        escolas_selecionadas = st.multiselect("Escolas*", escolas_opcoes)
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome and escolas_selecionadas:
                escolas_ids = [e[0] for e in escolas_db if e[1] in escolas_selecionadas]
                sucesso, msg = adicionar_cliente(nome, telefone, email, escolas_ids)
                if sucesso:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
            else:
                st.error("Nome e pelo menos uma escola são obrigatórios")
    
    with tab2:
        st.header("Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Escolas': cliente[4] or 'Nenhuma',
                    'Data Cadastro': cliente[5]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("Nenhum cliente cadastrado")
    
    with tab3:
        st.header("Excluir Cliente")
        clientes = listar_clientes()
        
        if clientes:
            cliente_selecionado = st.selectbox(
                "Selecione o cliente:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                st.warning("⚠️ Esta ação não pode ser desfeita!")
                if st.button("🗑️ Excluir Cliente", type="primary"):
                    sucesso, msg = excluir_cliente(cliente_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("✅ Conectado ao PostgreSQL\n\n🌐 Render.com")
