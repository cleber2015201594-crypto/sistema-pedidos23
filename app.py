import streamlit as st
import os
import hashlib
import psycopg2
from datetime import datetime, date

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Mobile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.75rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔐 AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Conexão com PostgreSQL"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            return psycopg2.connect(database_url, sslmode='require')
        return None
    except Exception as e:
        st.error(f"Erro conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Tabelas básicas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nome_completo VARCHAR(100),
                tipo VARCHAR(20) DEFAULT 'vendedor'
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                telefone VARCHAR(20),
                email VARCHAR(100),
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                categoria VARCHAR(100),
                tamanho VARCHAR(10),
                cor VARCHAR(50),
                preco DECIMAL(10,2),
                estoque INTEGER DEFAULT 0,
                escola_id INTEGER REFERENCES escolas(id)
            )
        ''')
        
        # Dados iniciais
        usuarios = [
            ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor', 'vendedor')
        ]
        
        for user in usuarios:
            cur.execute('''
                INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            ''', user)
        
        escolas = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas:
            cur.execute('''
                INSERT INTO escolas (nome) VALUES (%s)
                ON CONFLICT (nome) DO NOTHING
            ''', (escola,))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Erro init db: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT password_hash, nome_completo, tipo FROM usuarios WHERE username = %s', (username,))
        result = cur.fetchone()
        
        if result and check_hashes(password, result[0]):
            return True, result[1], result[2]
        return False, "Credenciais inválidas", None
        
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        if conn:
            conn.close()

# =========================================
# 📱 FUNÇÕES PRINCIPAIS
# =========================================

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro conexão"
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s)",
            (nome, telefone, email)
        )
        conn.commit()
        return True, "Cliente cadastrado!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except:
        return []
    finally:
        if conn:
            conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro conexão"
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "Produto cadastrado!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id 
            ORDER BY p.nome
        ''')
        return cur.fetchall()
    except:
        return []
    finally:
        if conn:
            conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except:
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 🚀 APP PRINCIPAL
# =========================================

# Inicialização
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Página de Login
if not st.session_state.logged_in:
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>👕 Sistema Fardamentos</h1>
        <p>Login para continuar</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login"):
        user = st.text_input("👤 Usuário")
        pwd = st.text_input("🔒 Senha", type="password")
        
        if st.form_submit_button("🚀 Entrar", use_container_width=True):
            if user and pwd:
                success, msg, user_type = verificar_login(user, pwd)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.name = msg
                    st.session_state.type = user_type
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Preencha todos os campos")
    st.stop()

# App Principal
st.sidebar.markdown(f"**👤 {st.session_state.name}**")
st.sidebar.markdown(f"**🎯 {st.session_state.type}**")

menu = st.sidebar.radio("Navegação", 
    ["📊 Dashboard", "👥 Clientes", "👕 Produtos"])

st.title(menu)

if menu == "📊 Dashboard":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        clientes = listar_clientes()
        st.metric("👥 Clientes", len(clientes))
    
    with col2:
        produtos = listar_produtos()
        st.metric("👕 Produtos", len(produtos))
    
    with col3:
        baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("⚠️ Alerta Estoque", baixo_estoque)
    
    st.subheader("⚡ Ações Rápidas")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("➕ Novo Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col2:
        if st.button("👕 Novo Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Listar"])
    
    with tab1:
        with st.form("novo_cliente"):
            nome = st.text_input("Nome completo*")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            
            if st.form_submit_button("✅ Cadastrar", use_container_width=True):
                if nome:
                    success, msg = adicionar_cliente(nome, telefone, email)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("Nome obrigatório")
    
    with tab2:
        clientes = listar_clientes()
        if clientes:
            for cli in clientes:
                with st.expander(f"👤 {cli[1]}"):
                    st.write(f"📞 {cli[2] or 'N/A'}")
                    st.write(f"📧 {cli[3] or 'N/A'}")
                    st.write(f"📅 {cli[4]}")
        else:
            st.info("Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Listar"])
    
    with tab1:
        with st.form("novo_produto"):
            nome = st.text_input("Nome do produto*")
            categoria = st.selectbox("Categoria", ["Camiseta", "Calça", "Agasalho"])
            tamanho = st.selectbox("Tamanho", ["P", "M", "G", "GG"])
            cor = st.text_input("Cor", "Branco")
            preco = st.number_input("Preço R$", min_value=0.0, value=29.9)
            estoque = st.number_input("Estoque", min_value=0, value=10)
            
            escolas = listar_escolas()
            escola_nome = st.selectbox("Escola", [e[1] for e in escolas])
            
            if st.form_submit_button("✅ Cadastrar", use_container_width=True):
                if nome:
                    escola_id = next(e[0] for e in escolas if e[1] == escola_nome)
                    success, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("Nome obrigatório")
    
    with tab2:
        produtos = listar_produtos()
        if produtos:
            for prod in produtos:
                with st.expander(f"👕 {prod[1]} - {prod[3]} - {prod[4]}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Categoria:** {prod[2]}")
                        st.write(f"**Preço:** R$ {prod[5]:.2f}")
                    with col2:
                        st.write(f"**Estoque:** {prod[6]}")
                        st.write(f"**Escola:** {prod[8]}")
        else:
            st.info("Nenhum produto cadastrado")

# Logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
