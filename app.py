import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

# =========================================
# 🎨 CONFIGURAÇÃO DE ESTILOS E CORES
# =========================================

st.set_page_config(
    page_title="FashionManager Pro",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para cores e estilo
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #6A0DAD;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.8rem;
        color: #4B0082;
        border-bottom: 3px solid #9370DB;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .success-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .warning-card {
        background: linear-gradient(135deg, #f46b45 0%, #eea849 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .info-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stButton>button {
        background: linear-gradient(135deg, #6A0DAD 0%, #9370DB 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #5a0a9c 0%, #8367c7 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔧 CONFIGURAÇÃO DO BANCO DE DADOS - POSTGRESQL
# =========================================

def get_connection():
    """Estabelece conexão com PostgreSQL no Render"""
    try:
        # Para Render - usa DATABASE_URL do environment
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Parse da URL do Render
            parsed_url = urllib.parse.urlparse(database_url)
            
            conn = psycopg2.connect(
                database=parsed_url.path[1:],
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port,
                sslmode='require'
            )
        else:
            # Para desenvolvimento local - SQLite como fallback
            import sqlite3
            conn = sqlite3.connect('fardamentos_local.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
        
        return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        # Verificar se é PostgreSQL ou SQLite
        if hasattr(conn, 'cursor'):
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nome_completo TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT TRUE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER REFERENCES clientes(id),
                    escola_id INTEGER REFERENCES escolas(id),
                    status TEXT DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_entrega_real DATE,
                    forma_pagamento TEXT DEFAULT 'Dinheiro',
                    quantidade_total INTEGER,
                    valor_total REAL,
                    observacoes TEXT
                )
            ''')
            
            # Inserir dados iniciais
            usuarios_padrao = [
                ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('venda123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                cur.execute('''
                    INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                ''', (username, password_hash, nome, tipo))
            
            escolas_padrao = ['Escola Municipal', 'Colégio Desperta', 'Instituto São Tadeu']
            for escola in escolas_padrao:
                cur.execute('INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING', (escola,))
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"❌ Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = %s AND ativo = TRUE
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

# =========================================
# 🗃️ FUNÇÕES DO BANCO DE DADOS
# =========================================

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s)",
            (nome, telefone, email)
        )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = %s
                ORDER BY p.categoria, p.nome
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY e.nome, p.categoria, p.nome
            ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.markdown("<h1 class='main-header'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        st.markdown("<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: white; text-align: center;'>🔐 Acesso ao Sistema</h2>", unsafe_allow_html=True)
        
        username = st.text_input("👤 **Usuário**", placeholder="Digite seu usuário")
        password = st.text_input("🔒 **Senha**", type='password', placeholder="Digite sua senha")
        
        if st.button("🚀 **Entrar no Sistema**", use_container_width=True):
            if username and password:
                sucesso, mensagem, tipo_usuario = verificar_login(username, password)
                if sucesso:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.nome_usuario = mensagem
                    st.session_state.tipo_usuario = tipo_usuario
                    st.success(f"✅ Bem-vindo, {mensagem}!")
                    st.rerun()
                else:
                    st.error(f"❌ {mensagem}")
            else:
                st.error("⚠️ Preencha todos os campos")
        
        st.markdown("""
        <div style='color: white; margin-top: 1rem; text-align: center;'>
            <p><strong>Usuários de Teste:</strong></p>
            <p>👤 admin / 🔒 admin123</p>
            <p>👤 vendedor / 🔒 venda123</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# 🎯 CONFIGURAÇÕES GLOBAIS
# =========================================

# Inicializar banco
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# Configurações
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto
categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🎨 SIDEBAR - MENU PRINCIPAL
# =========================================

with st.sidebar:
    st.markdown("<h1 style='color: #6A0DAD; text-align: center;'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Informações do usuário
    st.markdown(f"""
    <div style='background: #f0f2f6; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
        <p style='margin: 0;'>👤 <strong>{st.session_state.nome_usuario}</strong></p>
        <p style='margin: 0;'>🎯 {st.session_state.tipo_usuario.title()}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu de navegação
    menu_options = ["📊 Dashboard", "🛍️ Vendas", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios"]
    menu = st.radio("**Navegação**", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    
    if st.button("🚪 **Sair do Sistema**", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =========================================
# 📊 PÁGINA - DASHBOARD
# =========================================

if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard - FashionManager Pro</h1>", unsafe_allow_html=True)
    
    # Métricas em tempo real
    st.markdown("<h2 class='section-header'>🎯 Métricas em Tempo Real</h2>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_produtos = len(listar_produtos_por_escola())
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total de Produtos</div>
            <div class='metric-value'>{total_produtos}</div>
            <div>👕 Cadastrados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);'>
            <div class='metric-label'>Clientes Ativos</div>
            <div class='metric-value'>{len(clientes)}</div>
            <div>👥 Cadastrados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);'>
            <div class='metric-label'>Escolas Parceiras</div>
            <div class='metric-value'>{len(escolas)}</div>
            <div>🏫 Ativas</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola[0])
            produtos_baixo_estoque += len([p for p in produtos if p[6] < 5])
        
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);'>
            <div class='metric-label'>Alertas de Estoque</div>
            <div class='metric-value'>{produtos_baixo_estoque}</div>
            <div>⚠️ Produtos críticos</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h3 class='section-header'>📈 Produtos por Categoria</h3>", unsafe_allow_html=True)
        
        produtos = listar_produtos_por_escola()
        if produtos:
            categorias = {}
            for produto in produtos:
                categoria = produto[2]
                categorias[categoria] = categorias.get(categoria, 0) + 1
            
            if categorias:
                df_categorias = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
                fig = px.pie(df_categorias, values='Quantidade', names='Categoria', 
                            title='Distribuição de Produtos por Categoria',
                            color_discrete_sequence=px.colors.sequential.Viridis)
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("<h3 class='section-header'>📦 Estoque por Escola</h3>", unsafe_allow_html=True)
        
        estoque_por_escola = []
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola[0])
            total_estoque = sum(p[6] for p in produtos)
            estoque_por_escola.append({'Escola': escola[1], 'Estoque': total_estoque})
        
        if estoque_por_escola:
            df_estoque = pd.DataFrame(estoque_por_escola)
            fig = px.bar(df_estoque, x='Escola', y='Estoque', 
                        title='Total de Estoque por Escola',
                        color='Escola')
            st.plotly_chart(fig, use_container_width=True)
    
    # Ações Rápidas
    st.markdown("<h2 class='section-header'>⚡ Ações Rápidas</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🛍️ **Nova Venda**", use_container_width=True):
            st.session_state.menu = "🛍️ Vendas"
            st.rerun()
    
    with col2:
        if st.button("👥 **Cadastrar Cliente**", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 **Cadastrar Produto**", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

# =========================================
# 👕 PÁGINA - PRODUTOS
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Gestão de Produtos</h1>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Lista de Produtos"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>➕ Cadastrar Novo Produto</h2>", unsafe_allow_html=True)
        
        with st.form("novo_produto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                escola_produto = st.selectbox("🏫 **Escola:**", [e[1] for e in escolas])
                escola_id = next(e[0] for e in escolas if e[1] == escola_produto)
                
                nome = st.text_input("📝 **Nome do Produto***", placeholder="Ex: Camiseta Básica")
                categoria = st.selectbox("📂 **Categoria***", categorias_produtos)
                tamanho = st.selectbox("📏 **Tamanho***", todos_tamanhos)
            
            with col2:
                cor = st.text_input("🎨 **Cor***", value="Branco", placeholder="Ex: Azul Marinho")
                preco = st.number_input("💰 **Preço (R$)***", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 **Estoque Inicial***", min_value=0, value=10)
                descricao = st.text_area("📄 **Descrição**", placeholder="Detalhes do produto...")
            
            if st.form_submit_button("✅ **Cadastrar Produto**", type="primary"):
                if nome and cor:
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome e Cor")
    
    with tab2:
        st.markdown("<h2 class='section-header'>📋 Produtos Cadastrados</h2>", unsafe_allow_html=True)
        
        escola_filtro = st.selectbox("🏫 **Filtrar por Escola:**", ["Todas"] + [e[1] for e in escolas])
        
        if escola_filtro == "Todas":
            produtos = listar_produtos_por_escola()
        else:
            escola_id = next(e[0] for e in escolas if e[1] == escola_filtro)
            produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total", len(produtos))
            with col2:
                total_estoque = sum(p[6] for p in produtos)
                st.metric("🔄 Estoque", total_estoque)
            with col3:
                baixo_estoque = len([p for p in produtos if p[6] < 5])
                st.metric("⚠️ Críticos", baixo_estoque)
            
            # Tabela
            dados = []
            for produto in produtos:
                status = "✅" if produto[6] >= 5 else "⚠️" if produto[6] > 0 else "❌"
                dados.append({
                    'ID': produto[0],
                    'Produto': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Preço': f"R$ {produto[5]:.2f}",
                    'Estoque': f"{status} {produto[6]}",
                    'Escola': produto[9]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
        else:
            st.info("👕 Nenhum produto cadastrado")

# =========================================
# 👥 PÁGINA - CLIENTES
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Lista de Clientes"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>➕ Novo Cliente</h2>", unsafe_allow_html=True)
        
        with st.form("novo_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("👤 **Nome completo***", placeholder="Digite o nome completo")
                telefone = st.text_input("📞 **Telefone**", placeholder="(11) 99999-9999")
            
            with col2:
                email = st.text_input("📧 **Email**", placeholder="cliente@email.com")
            
            if st.form_submit_button("✅ **Cadastrar Cliente**", type="primary"):
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")
    
    with tab2:
        st.markdown("<h2 class='section-header'>📋 Clientes Cadastrados</h2>", unsafe_allow_html=True)
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Data Cadastro': cliente[4]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
            st.metric("👥 Total de Clientes", len(clientes))
        else:
            st.info("👥 Nenhum cliente cadastrado")

# =========================================
# 📦 PÁGINA - ESTOQUE
# =========================================

elif menu == "📦 Estoque":
    st.markdown("<h1 class='main-header'>📦 Controle de Estoque</h1>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    for escola in escolas:
        with st.expander(f"🏫 {escola[1]}", expanded=True):
            produtos = listar_produtos_por_escola(escola[0])
            
            if produtos:
                # Métricas
                col1, col2, col3, col4 = st.columns(4)
                total_produtos = len(produtos)
                total_estoque = sum(p[6] for p in produtos)
                produtos_baixo = len([p for p in produtos if p[6] < 5])
                produtos_sem = len([p for p in produtos if p[6] == 0])
                
                with col1:
                    st.metric("📦 Produtos", total_produtos)
                with col2:
                    st.metric("🔄 Estoque", total_estoque)
                with col3:
                    st.metric("⚠️ Baixo", produtos_baixo)
                with col4:
                    st.metric("❌ Sem", produtos_sem)
                
                # Tabela
                dados = []
                for produto in produtos:
                    status = "✅ Suficiente" if produto[6] >= 5 else "⚠️ Baixo" if produto[6] > 0 else "❌ Esgotado"
                    dados.append({
                        'Produto': produto[1],
                        'Categoria': produto[2],
                        'Tamanho': produto[3],
                        'Cor': produto[4],
                        'Estoque': produto[6],
                        'Status': status
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
                
                # Alertas
                produtos_alerta = [p for p in produtos if p[6] < 5]
                if produtos_alerta:
                    st.warning("🚨 **Alertas de Estoque:**")
                    for produto in produtos_alerta:
                        if produto[6] == 0:
                            st.error(f"**{produto[1]} - {produto[3]} - {produto[4]}**: ❌ ESGOTADO")
                        else:
                            st.warning(f"**{produto[1]} - {produto[3]} - {produto[4]}**: ⚠️ Apenas {produto[6]} unidades")
            else:
                st.info(f"👕 Nenhum produto para {escola[1]}")

# =========================================
# 📈 PÁGINA - RELATÓRIOS
# =========================================

elif menu == "📈 Relatórios":
    st.markdown("<h1 class='main-header'>📈 Relatórios e Analytics</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Estatísticas", "📦 Produtos", "👥 Clientes"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>📊 Estatísticas Gerais</h2>", unsafe_allow_html=True)
        
        escolas = listar_escolas()
        clientes = listar_clientes()
        produtos = listar_produtos_por_escola()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🏫 Escolas", len(escolas))
        with col2:
            st.metric("👥 Clientes", len(clientes))
        with col3:
            st.metric("👕 Produtos", len(produtos))
        
        # Gráfico de produtos por categoria
        if produtos:
            categorias = {}
            for produto in produtos:
                categoria = produto[2]
                categorias[categoria] = categorias.get(categoria, 0) + 1
            
            if categorias:
                df_cat = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
                fig = px.bar(df_cat, x='Categoria', y='Quantidade', title='Produtos por Categoria')
                st.plotly_chart(fig, use_container_width=True)

# =========================================
# 🛍️ PÁGINA - VENDAS (SIMPLIFICADA)
# =========================================

elif menu == "🛍️ Vendas":
    st.markdown("<h1 class='main-header'>🛍️ Sistema de Vendas</h1>", unsafe_allow_html=True)
    
    st.info("🚀 **Módulo de Vendas em Desenvolvimento**")
    st.write("Esta funcionalidade estará disponível em breve!")
    st.write("Enquanto isso, você pode:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("✅ Cadastrar produtos")
        st.write("✅ Gerenciar clientes")
        st.write("✅ Controlar estoque")
    
    with col2:
        st.write("✅ Visualizar relatórios")
        st.write("✅ Acompanhar métricas")
        st.write("✅ Configurar escolas")

# =========================================
# 🎯 RODAPÉ
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='text-align: center; color: #6A0DAD;'>
    <p><strong>👕 FashionManager Pro v2.0</strong></p>
    <p>🚀 Sistema completo de gestão</p>
</div>
""", unsafe_allow_html=True)
