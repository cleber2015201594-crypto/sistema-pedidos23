import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
import hashlib
import sqlite3
import time

# =========================================
# 🚀 CONFIGURAÇÃO PARA RENDER
# =========================================

# Verificar se está rodando no Render
IS_RENDER = 'RENDER' in os.environ

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Estabelece conexão com SQLite"""
    try:
        db_path = '/tmp/fardamentos.db' if IS_RENDER else 'fardamentos.db'
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco SQLite"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nome_completo TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('vendedor123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                try:
                    cur.execute('INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) VALUES (?, ?, ?, ?)', 
                               (username, password_hash, nome, tipo))
                except:
                    pass
            
            # Inserir escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                try:
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
                except:
                    pass
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco: {str(e)}")
        finally:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT password_hash, nome_completo, tipo FROM usuarios WHERE username = ? AND ativo = 1', (username,))
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
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username and password:
            sucesso, mensagem, tipo_usuario = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.nome_usuario = mensagem
                st.session_state.tipo_usuario = tipo_usuario
                st.sidebar.success(f"Bem-vindo, {mensagem}!")
                st.rerun()
            else:
                st.sidebar.error(mensagem)
        else:
            st.sidebar.error("Preencha todos os campos")

# =========================================
# 🚀 SISTEMA PRINCIPAL
# =========================================

# Configuração da página
st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do banco
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# CONFIGURAÇÕES
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto
categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS
# =========================================

def formatar_data_brasil(data_str):
    """Converte data para formato brasileiro"""
    if not data_str:
        return ""
    try:
        if isinstance(data_str, str):
            data_obj = datetime.strptime(data_str, "%Y-%m-%d")
            return data_obj.strftime("%d/%m/%Y")
        elif isinstance(data_str, datetime):
            return data_str.strftime("%d/%m/%Y")
        else:
            return str(data_str)
    except:
        return data_str

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        cur.execute("INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (?, ?, ?, ?)",
                   (nome, telefone, email, data_cadastro))
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        if escola_id:
            cur.execute('SELECT p.*, e.nome as escola_nome FROM produtos p LEFT JOIN escolas e ON p.escola_id = e.id WHERE p.escola_id = ? ORDER BY p.categoria, p.nome', (escola_id,))
        else:
            cur.execute('SELECT p.*, e.nome as escola_nome FROM produtos p LEFT JOIN escolas e ON p.escola_id = e.id ORDER BY e.nome, p.categoria, p.nome')
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title(f"{menu} - Sistema de Fardamentos")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Dashboard - Visão Geral")
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Escolas", len(escolas))
    
    with col2:
        st.metric("Total de Clientes", len(clientes))
    
    with col3:
        total_produtos = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola['id'])
            total_produtos += len(produtos)
        st.metric("Total de Produtos", total_produtos)
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola['id'])
            produtos_baixo_estoque += len([p for p in produtos if p.get('estoque', 0) < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque)
    
    # Ações Rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.info("Funcionalidade de pedidos em desenvolvimento")
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.info("Navegue para a aba Clientes")
    
    with col3:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.info("Navegue para a aba Produtos")

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        with st.form("form_cliente"):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente", type="primary"):
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente['id'],
                    'Nome': cliente['nome'],
                    'Telefone': cliente['telefone'] or 'N/A',
                    'Email': cliente['email'] or 'N/A',
                    'Data Cadastro': formatar_data_brasil(cliente['data_cadastro'])
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. O sistema precisa de escolas para cadastrar produtos.")
        st.stop()
    
    # Seleção da escola
    escola_selecionada_nome = st.selectbox(
        "🏫 Selecione a Escola:",
        [e['nome'] for e in escolas],
        key="produtos_escola"
    )
    escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada_nome)
    
    st.header(f"👕 Produtos - {escola_selecionada_nome}")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Novo", "📋 Lista de Produtos"])
    
    with tab1:
        st.subheader("➕ Cadastrar Novo Produto")
        
        with st.form("novo_produto_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("📝 Nome do Produto*", placeholder="Ex: Camiseta Polo")
                categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
            with col2:
                cor = st.text_input("🎨 Cor*", placeholder="Ex: Branco")
                preco = st.number_input("💰 Preço (R$)*", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 Estoque Inicial*", min_value=0, value=10)
            
            descricao = st.text_area("📄 Descrição (opcional)", placeholder="Detalhes do produto...")
            
            if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                if nome and cor:
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome e Cor")
    
    with tab2:
        st.subheader("📋 Lista de Produtos")
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_categoria = st.selectbox("Filtrar por categoria:", ["Todas"] + categorias_produtos)
            with col2:
                busca_nome = st.text_input("Buscar por nome:")
            
            # Aplicar filtros
            produtos_filtrados = produtos
            if filtro_categoria != "Todas":
                produtos_filtrados = [p for p in produtos_filtrados if p['categoria'] == filtro_categoria]
            if busca_nome:
                produtos_filtrados = [p for p in produtos_filtrados if busca_nome.lower() in p['nome'].lower()]
            
            # Exibir produtos
            for produto in produtos_filtrados:
                status_estoque = "✅" if produto['estoque'] >= 10 else "⚠️" if produto['estoque'] >= 5 else "❌"
                
                with st.expander(f"{status_estoque} {produto['nome']} - {produto['tamanho']} - {produto['cor']}"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.write(f"**Categoria:** {produto['categoria']}")
                        st.write(f"**Preço:** R$ {produto['preco']:.2f}")
                        st.write(f"**Estoque:** {produto['estoque']} unidades")
                        st.write(f"**Descrição:** {produto['descricao'] or 'Sem descrição'}")
        else:
            st.info("📭 Nenhum produto cadastrado para esta escola")

elif menu == "📦 Estoque":
    st.header("📦 Controle de Estoque")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    # Abas por escola
    tabs = st.tabs([f"🏫 {e['nome']}" for e in escolas])
    
    for idx, escola in enumerate(escolas):
        with tabs[idx]:
            st.subheader(f"Estoque - {escola['nome']}")
            
            produtos = listar_produtos_por_escola(escola['id'])
            
            if produtos:
                # Métricas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Produtos", len(produtos))
                with col2:
                    total_estoque = sum(p['estoque'] for p in produtos)
                    st.metric("Estoque Total", total_estoque)
                with col3:
                    produtos_baixo_estoque = len([p for p in produtos if p['estoque'] < 5])
                    st.metric("Estoque Baixo", produtos_baixo_estoque)
                
                # Lista de produtos
                for produto in produtos:
                    status_estoque = "✅" if produto['estoque'] >= 10 else "⚠️" if produto['estoque'] >= 5 else "❌"
                    
                    st.write(f"{status_estoque} **{produto['nome']}** - {produto['tamanho']} - {produto['cor']} | Estoque: **{produto['estoque']}**")
            else:
                st.info(f"📭 Nenhum produto cadastrado para {escola['nome']}")

elif menu == "📦 Pedidos":
    st.header("📦 Gestão de Pedidos")
    st.info("🚧 Módulo de pedidos em desenvolvimento")
    st.write("Esta funcionalidade permitirá:")
    st.write("✅ Criar novos pedidos")
    st.write("✅ Gerenciar status dos pedidos") 
    st.write("✅ Controlar entregas")
    st.write("✅ Emitir relatórios de vendas")

elif menu == "📈 Relatórios":
    st.header("📈 Relatórios e Estatísticas")
    st.info("📊 Módulo de relatórios em desenvolvimento")
    st.write("Relatórios disponíveis em breve:")
    st.write("📈 Vendas por período")
    st.write("📊 Produtos mais vendidos")
    st.write("👥 Clientes mais frequentes")
    st.write("📦 Controle de estoque")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v2.0\n\nDesenvolvido para gestão escolar")

# Botão para recarregar
if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()