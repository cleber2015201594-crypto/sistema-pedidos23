import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
import hashlib
import psycopg2
import urllib.parse

# =========================================
# 📱 CONFIGURAÇÃO MOBILE-FIRST
# =========================================

st.set_page_config(
    page_title="FashionManager Mobile",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar recolhida no mobile
)

# CSS para mobile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem !important;
        }
        .section-header {
            font-size: 1.4rem !important;
        }
        .metric-card {
            padding: 1rem !important;
            margin: 0.5rem 0 !important;
        }
        .metric-value {
            font-size: 1.8rem !important;
        }
    }
    
    .main-header {
        font-size: 2.5rem;
        color: #6A0DAD;
        text-align: center;
        margin-bottom: 1rem;
    }
    .mobile-button {
        width: 100%;
        margin: 0.5rem 0;
        padding: 1rem;
        font-size: 1.1rem;
    }
    .mobile-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🗃️ BANCO DE DADOS - MULTIPLAS OPÇÕES
# =========================================

def get_connection():
    """Conexão flexível com múltiplos bancos"""
    try:
        # 1. Tentar PostgreSQL (Render/Railway)
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            parsed_url = urllib.parse.urlparse(database_url)
            conn = psycopg2.connect(
                database=parsed_url.path[1:],
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port,
                sslmode='require'
            )
            return conn
        
        # 2. Tentar SQLite (local/fallback)
        import sqlite3
        conn = sqlite3.connect('fardamentos_mobile.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
        
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicialização do banco"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        if hasattr(conn, 'cursor'):  # PostgreSQL
            cur = conn.cursor()
            # Suas tabelas aqui (mesmo código anterior)
            # ...
            conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# =========================================
# 📱 INTERFACE MOBILE OTIMIZADA
# =========================================

def mobile_login():
    """Tela de login mobile"""
    st.markdown("<h1 class='main-header'>👕 FashionManager</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='mobile-card'>", unsafe_allow_html=True)
        username = st.text_input("👤 Usuário", placeholder="Seu usuário")
        password = st.text_input("🔒 Senha", type='password', placeholder="Sua senha")
        
        if st.button("🚀 Entrar", use_container_width=True, key="login_btn"):
            if username and password:
                # Sua lógica de login aqui
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Preencha todos os campos")
        
        st.markdown("---")
        st.markdown("**Usuários de teste:**")
        st.write("👤 admin / 🔒 admin123")
        st.write("👤 vendedor / 🔒 venda123")
        st.markdown("</div>", unsafe_allow_html=True)

def mobile_dashboard():
    """Dashboard mobile"""
    st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)
    
    # Métricas em cards
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='mobile-card'>", unsafe_allow_html=True)
        st.metric("👕 Produtos", "45")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='mobile-card'>", unsafe_allow_html=True)
        st.metric("👥 Clientes", "23")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Menu de ações rápidas
    st.markdown("### 🚀 Ações Rápidas")
    
    if st.button("🛍️ Nova Venda", use_container_width=True, key="venda_btn"):
        st.session_state.current_page = "vendas"
        st.rerun()
    
    if st.button("👕 Cadastrar Produto", use_container_width=True, key="produto_btn"):
        st.session_state.current_page = "produtos"
        st.rerun()
    
    if st.button("👥 Cadastrar Cliente", use_container_width=True, key="cliente_btn"):
        st.session_state.current_page = "clientes"
        st.rerun()

def mobile_produtos():
    """Tela de produtos mobile"""
    st.markdown("<h1 class='main-header'>👕 Produtos</h1>", unsafe_allow_html=True)
    
    # Botão voltar
    if st.button("⬅️ Voltar", key="back_produtos"):
        st.session_state.current_page = "dashboard"
        st.rerun()
    
    # Formulário simplificado
    with st.form("novo_produto_mobile"):
        nome = st.text_input("Nome do produto")
        categoria = st.selectbox("Categoria", ["Camisetas", "Calças", "Agasalhos"])
        tamanho = st.selectbox("Tamanho", ["P", "M", "G", "GG"])
        
        if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True):
            if nome:
                st.success("Produto cadastrado!")
            else:
                st.error("Nome é obrigatório")

def mobile_clientes():
    """Tela de clientes mobile"""
    st.markdown("<h1 class='main-header'>👥 Clientes</h1>", unsafe_allow_html=True)
    
    if st.button("⬅️ Voltar", key="back_clientes"):
        st.session_state.current_page = "dashboard"
        st.rerun()
    
    with st.form("novo_cliente_mobile"):
        nome = st.text_input("Nome completo")
        telefone = st.text_input("Telefone")
        email = st.text_input("Email")
        
        if st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True):
            if nome:
                st.success("Cliente cadastrado!")
            else:
                st.error("Nome é obrigatório")

# =========================================
# 🎯 APLICAÇÃO PRINCIPAL MOBILE
# =========================================

# Inicialização
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"

# Navegação
if not st.session_state.logged_in:
    mobile_login()
else:
    # Menu mobile no topo
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊", use_container_width=True):
            st.session_state.current_page = "dashboard"
    with col2:
        if st.button("🛍️", use_container_width=True):
            st.session_state.current_page = "vendas"
    with col3:
        if st.button("👕", use_container_width=True):
            st.session_state.current_page = "produtos"
    with col4:
        if st.button("👥", use_container_width=True):
            st.session_state.current_page = "clientes"
    
    # Conteúdo das páginas
    if st.session_state.current_page == "dashboard":
        mobile_dashboard()
    elif st.session_state.current_page == "produtos":
        mobile_produtos()
    elif st.session_state.current_page == "clientes":
        mobile_clientes()
    elif st.session_state.current_page == "vendas":
        st.info("Módulo de vendas em desenvolvimento")
    
    # Logout no final
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
