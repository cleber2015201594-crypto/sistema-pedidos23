import streamlit as st
import pandas as pd
import plotly.express as px
import os
import psycopg2
import urllib.parse
import sqlite3
from datetime import datetime

# =========================================
# 🎨 CONFIGURAÇÃO DO APP
# =========================================

st.set_page_config(
    page_title="FashionManager Pro",
    page_icon="👕",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #6A0DAD;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .school-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🗃️ CONEXÃO COM BANCO
# =========================================

def get_connection():
    """Estabelece conexão com PostgreSQL (Render) ou SQLite (local)"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # PostgreSQL no Render - usar a URL diretamente
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        else:
            # SQLite local para desenvolvimento
            import sqlite3
            conn = sqlite3.connect('fashionmanager.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def get_placeholder():
    """Retorna o placeholder correto para o banco"""
    return '%s' if os.environ.get('DATABASE_URL') else '?'

def init_db():
    """Inicializa o banco de dados com tabelas necessárias"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Verificar se estamos usando PostgreSQL ou SQLite
        is_postgres = os.environ.get('DATABASE_URL') is not None
        
        if is_postgres:
            # PostgreSQL - usar SERIAL para auto-increment
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    escola_id INTEGER,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER,
                    escola_id INTEGER,
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pendente',
                    total DECIMAL(10,2) DEFAULT 0
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS itens_pedido (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER,
                    produto_id INTEGER,
                    quantidade INTEGER,
                    preco_unitario DECIMAL(10,2)
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', 'admin123', 'Administrador Principal', 'admin'),
                ('vendedor1', 'vendedor123', 'João Vendedor', 'vendedor'),
                ('vendedor2', 'vendedor123', 'Maria Vendedora', 'vendedor')
            ]
            
            for usuario in usuarios_padrao:
                cur.execute('''
                    INSERT INTO usuarios (username, password, nome, tipo) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                ''', usuario)
            
            # Inserir escola padrão
            cur.execute('''
                INSERT INTO escolas (nome, endereco, telefone, email) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (nome) DO NOTHING
            ''', ('Escola Principal', 'Endereço padrão', '(11) 99999-9999', 'contato@escola.com'))
                
        else:
            # SQLite local
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    escola_id INTEGER,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER,
                    escola_id INTEGER,
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pendente',
                    total REAL DEFAULT 0
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS itens_pedido (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER,
                    produto_id INTEGER,
                    quantidade INTEGER,
                    preco_unitario REAL
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', 'admin123', 'Administrador Principal', 'admin'),
                ('vendedor1', 'vendedor123', 'João Vendedor', 'vendedor'),
                ('vendedor2', 'vendedor123', 'Maria Vendedora', 'vendedor')
            ]
            
            for usuario in usuarios_padrao:
                cur.execute('''
                    INSERT OR IGNORE INTO usuarios (username, password, nome, tipo) 
                    VALUES (?, ?, ?, ?)
                ''', usuario)
            
            # Inserir escola padrão
            cur.execute('''
                INSERT OR IGNORE INTO escolas (nome, endereco, telefone, email) 
                VALUES (?, ?, ?, ?)
            ''', ('Escola Principal', 'Endereço padrão', '(11) 99999-9999', 'contato@escola.com'))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def check_login(username, password):
    """Verifica as credenciais do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None, None
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'SELECT id, password, nome, tipo FROM usuarios WHERE username = {placeholder}'
        cur.execute(query, (username,))
        result = cur.fetchone()
        
        if result:
            user_id, stored_password, nome, tipo = result
            if stored_password == password:
                return True, nome, tipo, user_id
        
        return False, "Credenciais inválidas", None, None
    except Exception as e:
        return False, f"Erro: {str(e)}", None, None
    finally:
        if conn:
            conn.close()

def login_page():
    """Página de login"""
    st.markdown("<h1 class='main-header'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("🔐 **Faça login para continuar**")
        
        username = st.text_input("👤 Usuário")
        password = st.text_input("🔒 Senha", type='password')
        
        if st.button("🚀 Entrar", use_container_width=True):
            if username and password:
                success, message, user_type, user_id = check_login(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = message
                    st.session_state.user_type = user_type
                    st.session_state.user_id = user_id
                    st.success(f"✅ Bem-vindo, {message}!")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("⚠️ Preencha todos os campos")
        
        st.markdown("---")
        st.markdown("**👤 Usuários de teste:**")
        st.markdown("- **admin** / **admin123** (Administrador)")
        st.markdown("- **vendedor1** / **vendedor123** (Vendedor)")
        st.markdown("- **vendedor2** / **vendedor123** (Vendedor)")

# =========================================
# 👥 FUNÇÕES DE GERENCIAMENTO DE USUÁRIOS
# =========================================

def listar_usuarios():
    """Lista todos os usuários"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios ORDER BY username')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar usuários: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_usuario(username, password, nome, tipo):
    """Adiciona um novo usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'INSERT INTO usuarios (username, password, nome, tipo) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})'
        cur.execute(query, (username, password, nome, tipo))
        conn.commit()
        return True, "✅ Usuário cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def excluir_usuario(usuario_id):
    """Exclui um usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM usuarios WHERE id = {placeholder}'
        cur.execute(query, (usuario_id,))
        conn.commit()
        return True, "✅ Usuário excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def alterar_senha(usuario_id, nova_senha):
    """Altera a senha de um usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'UPDATE usuarios SET password = {placeholder} WHERE id = {placeholder}'
        cur.execute(query, (nova_senha, usuario_id))
        conn.commit()
        return True, "✅ Senha alterada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - ESCOLAS
# =========================================

def adicionar_escola(nome, endereco, telefone, email):
    """Adiciona uma nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'INSERT INTO escolas (nome, endereco, telefone, email) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})'
        cur.execute(query, (nome, endereco, telefone, email))
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_escolas():
    """Lista todas as escolas"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM escolas ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def excluir_escola(escola_id):
    """Exclui uma escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM escolas WHERE id = {placeholder}'
        cur.execute(query, (escola_id,))
        conn.commit()
        return True, "✅ Escola excluída com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - PRODUTOS
# =========================================

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    """Adiciona um novo produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id) 
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos(escola_id=None):
    """Lista produtos, opcionalmente filtrando por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            query = f'SELECT * FROM produtos WHERE escola_id = {placeholder} ORDER BY nome'
            cur.execute(query, (escola_id,))
        else:
            cur.execute('SELECT * FROM produtos ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def excluir_produto(produto_id):
    """Exclui um produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM produtos WHERE id = {placeholder}'
        cur.execute(query, (produto_id,))
        conn.commit()
        return True, "✅ Produto excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - CLIENTES
# =========================================

def adicionar_cliente(nome, telefone, email, escola_id):
    """Adiciona um novo cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'INSERT INTO clientes (nome, telefone, email, escola_id) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})'
        cur.execute(query, (nome, telefone, email, escola_id))
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes(escola_id=None):
    """Lista clientes, opcionalmente filtrando por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            query = f'SELECT * FROM clientes WHERE escola_id = {placeholder} ORDER BY nome'
            cur.execute(query, (escola_id,))
        else:
            cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def excluir_cliente(cliente_id):
    """Exclui um cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'DELETE FROM clientes WHERE id = {placeholder}'
        cur.execute(query, (cliente_id,))
        conn.commit()
        return True, "✅ Cliente excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA - PEDIDOS
# =========================================

def criar_pedido(cliente_id, escola_id, itens):
    """Cria um novo pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        # Criar o pedido
        query = f'INSERT INTO pedidos (cliente_id, escola_id, total) VALUES ({placeholder}, {placeholder}, 0)'
        cur.execute(query, (cliente_id, escola_id))
        
        # Obter ID do pedido criado
        if os.environ.get('DATABASE_URL'):
            cur.execute('SELECT LASTVAL()')
        else:
            cur.execute('SELECT last_insert_rowid()')
        pedido_id = cur.fetchone()[0]
        
        # Adicionar itens e calcular total
        total_pedido = 0
        for produto_id, quantidade in itens:
            # Buscar preço do produto
            query = f'SELECT preco FROM produtos WHERE id = {placeholder}'
            cur.execute(query, (produto_id,))
            preco_result = cur.fetchone()
            
            if not preco_result:
                return False, f"❌ Produto com ID {produto_id} não encontrado"
            
            preco_unitario = preco_result[0]
            
            # Inserir item do pedido
            query = f'''
                INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) 
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            '''
            cur.execute(query, (pedido_id, produto_id, quantidade, preco_unitario))
            
            # Atualizar estoque
            query = f'UPDATE produtos SET estoque = estoque - {placeholder} WHERE id = {placeholder}'
            cur.execute(query, (quantidade, produto_id))
            
            total_pedido += preco_unitario * quantidade
        
        # Atualizar total do pedido
        query = f'UPDATE pedidos SET total = {placeholder} WHERE id = {placeholder}'
        cur.execute(query, (total_pedido, pedido_id))
        
        conn.commit()
        return True, f"✅ Pedido #{pedido_id} criado com sucesso! Total: R$ {total_pedido:.2f}"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_pedidos(escola_id=None):
    """Lista pedidos, opcionalmente filtrando por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            query = f'''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome 
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.escola_id = {placeholder}
                ORDER BY p.data_pedido DESC
            '''
            cur.execute(query, (escola_id,))
        else:
            query = '''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome 
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                ORDER BY p.data_pedido DESC
            '''
            cur.execute(query)
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar pedidos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def atualizar_status_pedido(pedido_id, status):
    """Atualiza o status de um pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'UPDATE pedidos SET status = {placeholder} WHERE id = {placeholder}'
        cur.execute(query, (status, pedido_id))
        conn.commit()
        return True, "✅ Status do pedido atualizado!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📈 FUNÇÕES DE RELATÓRIOS
# =========================================

def gerar_relatorio_vendas():
    """Gera relatório de vendas"""
    pedidos = listar_pedidos()
    
    if not pedidos:
        return pd.DataFrame()
    
    dados = []
    for pedido in pedidos:
        dados.append({
            'Pedido': pedido[0],
            'Data': pedido[3],
            'Cliente': pedido[6] if len(pedido) > 6 else 'N/A',
            'Escola': pedido[7] if len(pedido) > 7 else 'N/A',
            'Total': float(pedido[5]) if pedido[5] else 0.0,
            'Status': pedido[4]
        })
    
    return pd.DataFrame(dados)

# =========================================
# 🎯 INICIALIZAÇÃO DO SISTEMA
# =========================================

# Inicializar banco de dados
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True
    else:
        st.error("❌ Falha ao inicializar o banco de dados")

# Verificar login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =========================================
# 🎨 MENU PRINCIPAL
# =========================================

with st.sidebar:
    st.markdown(f"**👤 {st.session_state.user_name}**")
    st.markdown(f"**🎯 {st.session_state.user_type.upper()}**")
    st.markdown("---")
    
    # Menu base para todos os usuários
    menu_options = [
        "📊 Dashboard",
        "🏫 Escolas", 
        "👕 Produtos",
        "👥 Clientes",
        "📦 Pedidos",
        "📈 Relatórios"
    ]
    
    # Apenas administradores podem gerenciar usuários
    if st.session_state.user_type == 'admin':
        menu_options.append("👥 Usuários")
    
    menu = st.radio("📋 Navegação", menu_options)
    
    st.markdown("---")
    
    # Botão para alterar senha (disponível para todos)
    if st.button("🔐 Alterar Minha Senha", use_container_width=True):
        st.session_state.alterar_senha = True
    
    if st.button("🚪 Sair", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =========================================
# 🔐 ALTERAÇÃO DE SENHA (MODAL)
# =========================================

if st.session_state.get('alterar_senha'):
    with st.container():
        st.markdown("<h3>🔐 Alterar Minha Senha</h3>", unsafe_allow_html=True)
        
        nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha_input")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha_input")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Salvar Nova Senha", use_container_width=True):
                if nova_senha and confirmar_senha:
                    if nova_senha == confirmar_senha:
                        success, msg = alterar_senha(st.session_state.user_id, nova_senha)
                        if success:
                            st.success(msg)
                            st.session_state.alterar_senha = False
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ As senhas não coincidem!")
                else:
                    st.error("❌ Preencha todos os campos!")
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.alterar_senha = False
                st.rerun()

# =========================================
# 📊 DASHBOARD PRINCIPAL
# =========================================

if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)
    
    # Métricas gerais
    st.subheader("📈 Métricas Gerais")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        escolas_count = len(listar_escolas())
        st.metric("🏫 Escolas", escolas_count)
    
    with col2:
        clientes_count = len(listar_clientes())
        st.metric("👥 Clientes", clientes_count)
    
    with col3:
        produtos_count = len(listar_produtos())
        st.metric("👕 Produtos", produtos_count)
    
    with col4:
        pedidos_count = len(listar_pedidos())
        st.metric("📦 Pedidos", pedidos_count)
    
    # Ações rápidas
    st.subheader("🚀 Ações Rápidas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Nova Escola", use_container_width=True, key="btn_escola_dash"):
            st.session_state.menu = "🏫 Escolas"
            st.rerun()
    
    with col2:
        if st.button("👕 Novo Produto", use_container_width=True, key="btn_produto_dash"):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col3:
        if st.button("👥 Novo Cliente", use_container_width=True, key="btn_cliente_dash"):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col4:
        if st.button("📦 Novo Pedido", use_container_width=True, key="btn_pedido_dash"):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()

# =========================================
# 🏫 GESTÃO DE ESCOLAS
# =========================================

elif menu == "🏫 Escolas":
    st.markdown("<h1 class='main-header'>🏫 Gestão de Escolas</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Escolas", "➕ Cadastrar Escola"])
    
    with tab1:
        st.subheader("📋 Lista de Escolas Cadastradas")
        escolas = listar_escolas()
        
        if escolas:
            for escola in escolas:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{escola[1]}**")
                    if escola[2]:
                        st.write(f"📍 {escola[2]}")
                    if escola[3]:
                        st.write(f"📞 {escola[3]}")
                    if escola[4]:
                        st.write(f"📧 {escola[4]}")
                    st.write(f"📅 Cadastrada em: {escola[5]}")
                
                with col2:
                    produtos_count = len(listar_produtos(escola[0]))
                    st.metric("Produtos", produtos_count)
                
                with col3:
                    if st.button("🗑️", key=f"del_escola_{escola[0]}"):
                        success, msg = excluir_escola(escola[0])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                
                st.markdown("---")
        else:
            st.info("📝 Nenhuma escola cadastrada")
    
    with tab2:
        st.subheader("➕ Cadastrar Nova Escola")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola*", placeholder="Ex: Escola Municipal São Paulo")
            endereco = st.text_input("Endereço", placeholder="Ex: Rua Principal, 123 - Centro")
            telefone = st.text_input("Telefone", placeholder="Ex: (11) 99999-9999")
            email = st.text_input("Email", placeholder="Ex: contato@escola.com")
            
            if st.form_submit_button("✅ Cadastrar Escola", use_container_width=True):
                if nome:
                    success, msg = adicionar_escola(nome, endereco, telefone, email)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome da escola é obrigatório!")

# =========================================
# 👕 GESTÃO DE PRODUTOS
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Gestão de Produtos</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Produtos", "➕ Cadastrar Produto", "📊 Estatísticas"])
    
    with tab1:
        st.subheader("📋 Lista de Produtos")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            escolas = listar_escolas()
            escola_options = {0: "Todas as escolas"}
            for escola in escolas:
                escola_options[escola[0]] = escola[1]
            escola_id = st.selectbox("Filtrar por escola", options=list(escola_options.keys()), 
                                   format_func=lambda x: escola_options[x])
        
        with col2:
            produtos_todos = listar_produtos()
            categorias = ["Todas"] + list(set([p[2] for p in produtos_todos if p[2]]))
            categoria = st.selectbox("Filtrar por categoria", options=categorias)
        
        # Lista de produtos
        produtos = listar_produtos(escola_id if escola_id != 0 else None)
        if categoria != "Todas":
            produtos = [p for p in produtos if p[2] == categoria]
        
        if produtos:
            for produto in produtos:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{produto[1]}**")
                    escola_nome = next((escola[1] for escola in escolas if escola[0] == produto[7]), "N/A")
                    st.write(f"🏫 {escola_nome} | 📁 {produto[2]} | 📏 {produto[3]} | 🎨 {produto[4]}")
                
                with col2:
                    st.write(f"💵 R$ {float(produto[5]):.2f}" if produto[5] else "💵 R$ 0.00")
                
                with col3:
                    estoque = produto[6] if produto[6] else 0
                    status = "✅" if estoque >= 10 else "⚠️" if estoque > 0 else "❌"
                    st.write(f"{status} {estoque} un")
                
                with col4:
                    if st.button("🗑️", key=f"del_prod_{produto[0]}"):
                        success, msg = excluir_produto(produto[0])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                
                st.markdown("---")
        else:
            st.info("📝 Nenhum produto cadastrado")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Produto")
        escolas = listar_escolas()
        
        if not escolas:
            st.error("❌ É necessário cadastrar uma escola primeiro.")
        else:
            with st.form("novo_produto"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome do Produto*", placeholder="Ex: Camiseta Polo Branca")
                    categoria = st.selectbox("Categoria*", ["Camisetas", "Calças", "Agasalhos", "Acessórios", "Uniformes"])
                    tamanho = st.selectbox("Tamanho*", ["P", "M", "G", "GG", "XG", "Único"])
                
                with col2:
                    cor = st.text_input("Cor*", placeholder="Ex: Branco")
                    preco = st.number_input("Preço R$*", min_value=0.0, value=29.90, step=0.01)
                    estoque = st.number_input("Estoque*", min_value=0, value=10)
                    escola_id = st.selectbox("Escola*", options=[e[0] for e in escolas], 
                                           format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
                
                if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True):
                    if nome and cor and escola_id:
                        success, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Campos obrigatórios: Nome, Cor e Escola")
    
    with tab3:
        st.subheader("📊 Estatísticas de Produtos")
        
        # Métricas visuais
        col1, col2, col3 = st.columns(3)
        with col1:
            total_produtos = len(listar_produtos())
            st.metric("Total de Produtos", total_produtos)
        with col2:
            produtos_todos = listar_produtos()
            total_estoque = sum(p[6] for p in produtos_todos if p[6])
            st.metric("Estoque Total", total_estoque)
        with col3:
            produtos_baixo_estoque = len([p for p in produtos_todos if p[6] and p[6] < 5])
            st.metric("Estoque Baixo", produtos_baixo_estoque)
        
        # Gráfico de categorias
        st.subheader("📈 Distribuição por Categoria")
        produtos = listar_produtos()
        if produtos:
            categorias = {}
            for produto in produtos:
                cat = produto[2] or "Sem categoria"
                categorias[cat] = categorias.get(cat, 0) + 1
            
            if categorias:
                df = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
                fig = px.pie(df, values='Quantidade', names='Categoria', title='Produtos por Categoria')
                st.plotly_chart(fig, use_container_width=True)

# =========================================
# 👥 GESTÃO DE CLIENTES
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Cadastrar Cliente"])
    
    with tab1:
        st.subheader("📋 Lista de Clientes")
        
        # Filtro por escola
        escolas = listar_escolas()
        escola_options = {0: "Todas as escolas"}
        for escola in escolas:
            escola_options[escola[0]] = escola[1]
        escola_id = st.selectbox("Filtrar por escola", options=list(escola_options.keys()), 
                               format_func=lambda x: escola_options[x])
        
        clientes = listar_clientes(escola_id if escola_id != 0 else None)
        
        if clientes:
            for cliente in clientes:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{cliente[1]}**")
                    if cliente[2]:
                        st.write(f"📞 {cliente[2]}")
                    if cliente[3]:
                        st.write(f"📧 {cliente[3]}")
                    escola_nome = next((escola[1] for escola in escolas if escola[0] == cliente[4]), "N/A")
                    st.write(f"🏫 {escola_nome}")
                    st.write(f"📅 Cadastrado em: {cliente[5]}")
                
                with col2:
                    # Contar pedidos do cliente
                    pedidos_cliente = len([p for p in listar_pedidos() if p[1] == cliente[0]])
                    st.metric("Pedidos", pedidos_cliente)
                
                with col3:
                    if st.button("🗑️", key=f"del_cliente_{cliente[0]}"):
                        success, msg = excluir_cliente(cliente[0])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                
                st.markdown("---")
        else:
            st.info("📝 Nenhum cliente cadastrado")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Cliente")
        escolas = listar_escolas()
        
        if not escolas:
            st.error("❌ É necessário cadastrar uma escola primeiro.")
        else:
            with st.form("novo_cliente"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome completo*", placeholder="Ex: João Silva")
                    telefone = st.text_input("Telefone", placeholder="Ex: (11) 99999-9999")
                
                with col2:
                    email = st.text_input("Email", placeholder="Ex: joao.silva@email.com")
                    escola_id = st.selectbox("Escola*", options=[e[0] for e in escolas], 
                                           format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
                
                if st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True):
                    if nome and escola_id:
                        success, msg = adicionar_cliente(nome, telefone, email, escola_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome e escola são obrigatórios!")

# =========================================
# 📦 GESTÃO DE PEDIDOS
# =========================================

elif menu == "📦 Pedidos":
    st.markdown("<h1 class='main-header'>📦 Gestão de Pedidos</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🆕 Novo Pedido", "📋 Pedidos Realizados"])
    
    with tab1:
        st.subheader("🆕 Criar Novo Pedido")
        
        with st.form("novo_pedido"):
            # Selecionar escola
            escolas = listar_escolas()
            if not escolas:
                st.error("❌ É necessário cadastrar uma escola primeiro.")
                st.stop()
            
            escola_id = st.selectbox("🏫 Escola*", options=[e[0] for e in escolas], 
                                   format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
            
            # Selecionar cliente
            clientes = listar_clientes(escola_id)
            if not clientes:
                st.error("❌ Não há clientes cadastrados para esta escola.")
                st.stop()
            
            cliente_id = st.selectbox("👥 Cliente*", options=[c[0] for c in clientes], 
                                    format_func=lambda x: next((c[1] for c in clientes if c[0] == x), "N/A"))
            
            # Selecionar produtos
            st.subheader("🛒 Itens do Pedido")
            produtos = listar_produtos(escola_id)
            if not produtos:
                st.error("❌ Não há produtos cadastrados para esta escola.")
                st.stop()
            
            itens = []
            for i in range(3):  # Permitir até 3 itens
                col1, col2 = st.columns([3, 1])
                with col1:
                    produto_id = st.selectbox(f"Produto {i+1}", 
                                            options=[0] + [p[0] for p in produtos],
                                            format_func=lambda x: "Selecione..." if x == 0 else next((p[1] for p in produtos if p[0] == x), "N/A"),
                                            key=f"prod_{i}")
                with col2:
                    quantidade = st.number_input(f"Quantidade", min_value=0, value=0, key=f"qtd_{i}")
                
                if produto_id != 0 and quantidade > 0:
                    itens.append((produto_id, quantidade))
            
            # Finalizar pedido
            if st.form_submit_button("✅ Finalizar Pedido", use_container_width=True):
                if itens:
                    success, msg = criar_pedido(cliente_id, escola_id, itens)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Adicione pelo menos um item ao pedido.")
    
    with tab2:
        st.subheader("📋 Pedidos Realizados")
        
        # Filtro por escola
        escolas = listar_escolas()
        escola_options = {0: "Todas as escolas"}
        for escola in escolas:
            escola_options[escola[0]] = escola[1]
        escola_id = st.selectbox("Filtrar pedidos por escola", options=list(escola_options.keys()), 
                               format_func=lambda x: escola_options[x], key="filtro_pedidos")
        
        pedidos = listar_pedidos(escola_id if escola_id != 0 else None)
        
        if pedidos:
            for pedido in pedidos:
                with st.expander(f"📦 Pedido #{pedido[0]} - {pedido[7]} (Cliente: {pedido[6]})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Data:** {pedido[3]}")
                        st.write(f"**Status:** {pedido[4]}")
                    
                    with col2:
                        st.write(f"**Total:** R$ {float(pedido[5]):.2f}")
                    
                    with col3:
                        if pedido[4] == 'pendente':
                            if st.button("✅ Entregue", key=f"entregue_{pedido[0]}"):
                                success, msg = atualizar_status_pedido(pedido[0], 'entregue')
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("📝 Nenhum pedido realizado")

# =========================================
# 👥 GERENCIAMENTO DE USUÁRIOS (APENAS ADMIN)
# =========================================

elif menu == "👥 Usuários" and st.session_state.user_type == 'admin':
    st.markdown("<h1 class='main-header'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Usuários", "➕ Adicionar Usuário"])
    
    with tab1:
        st.subheader("📋 Lista de Usuários")
        usuarios = listar_usuarios()
        
        if usuarios:
            for usuario in usuarios:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{usuario[3]}**")
                    st.write(f"👤 {usuario[1]} | 🎯 {usuario[4]}")
                    st.write(f"📅 Cadastrado em: {usuario[5]}")
                
                with col2:
                    # Botão para alterar senha do usuário
                    if st.button("🔐", key=f"change_pwd_{usuario[0]}"):
                        st.session_state.alterar_senha_usuario = usuario[0]
                        st.session_state.nome_usuario = usuario[3]
                
                with col3:
                    # Não permitir excluir o próprio usuário
                    if usuario[0] != st.session_state.user_id:
                        if st.button("🗑️", key=f"del_user_{usuario[0]}"):
                            success, msg = excluir_usuario(usuario[0])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.write("👤 Você")
                
                with col4:
                    # Alterar tipo de usuário
                    if usuario[0] != st.session_state.user_id:
                        novo_tipo = st.selectbox(
                            "Tipo",
                            ["vendedor", "admin"],
                            index=0 if usuario[4] == "vendedor" else 1,
                            key=f"tipo_{usuario[0]}"
                        )
                        if novo_tipo != usuario[4]:
                            conn = get_connection()
                            if conn:
                                try:
                                    cur = conn.cursor()
                                    placeholder = get_placeholder()
                                    query = f'UPDATE usuarios SET tipo = {placeholder} WHERE id = {placeholder}'
                                    cur.execute(query, (novo_tipo, usuario[0]))
                                    conn.commit()
                                    st.success(f"✅ Tipo de {usuario[3]} alterado para {novo_tipo}!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro: {e}")
                                finally:
                                    conn.close()
                
                st.markdown("---")
        else:
            st.info("📝 Nenhum usuário cadastrado")
    
    with tab2:
        st.subheader("➕ Adicionar Novo Usuário")
        with st.form("novo_usuario"):
            username = st.text_input("👤 Nome de usuário*")
            password = st.text_input("🔒 Senha*", type='password')
            nome = st.text_input("📝 Nome completo*")
            tipo = st.selectbox("🎯 Tipo de usuário", ["vendedor", "admin"])
            
            if st.form_submit_button("✅ Cadastrar Usuário", use_container_width=True):
                if username and password and nome:
                    success, msg = adicionar_usuario(username, password, nome, tipo)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Todos os campos são obrigatórios!")

# =========================================
# 📈 RELATÓRIOS
# =========================================

elif menu == "📈 Relatórios":
    st.markdown("<h1 class='main-header'>📈 Relatórios</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 Vendas", "📦 Estoque"])
    
    with tab1:
        st.subheader("📊 Relatório de Vendas")
        
        df_vendas = gerar_relatorio_vendas()
        
        if not df_vendas.empty:
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_vendas = len(df_vendas)
                st.metric("Total de Vendas", total_vendas)
            with col2:
                faturamento_total = df_vendas['Total'].sum()
                st.metric("Faturamento Total", f"R$ {faturamento_total:.2f}")
            with col3:
                ticket_medio = faturamento_total / total_vendas if total_vendas > 0 else 0
                st.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
            
            # Tabela de vendas
            st.dataframe(df_vendas, use_container_width=True)
            
            # Gráfico de vendas por escola
            st.subheader("📈 Vendas por Escola")
            vendas_por_escola = df_vendas.groupby('Escola')['Total'].sum().reset_index()
            fig = px.bar(vendas_por_escola, x='Escola', y='Total', title='Faturamento por Escola')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📝 Nenhuma venda registrada")
    
    with tab2:
        st.subheader("📦 Relatório de Estoque")
        
        produtos = listar_produtos()
        if produtos:
            df_estoque = pd.DataFrame([{
                'Produto': p[1],
                'Categoria': p[2],
                'Tamanho': p[3],
                'Cor': p[4],
                'Preço': float(p[5]),
                'Estoque': p[6],
                'Escola': next((e[1] for e in listar_escolas() if e[0] == p[7]), 'N/A')
            } for p in produtos])
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                categoria_filtro = st.selectbox("Filtrar por categoria", 
                                              options=["Todas"] + list(df_estoque['Categoria'].unique()))
            with col2:
                estoque_minimo = st.number_input("Estoque mínimo", min_value=0, value=5)
            
            # Aplicar filtros
            if categoria_filtro != "Todas":
                df_estoque = df_estoque[df_estoque['Categoria'] == categoria_filtro]
            
            df_baixo_estoque = df_estoque[df_estoque['Estoque'] < estoque_minimo]
            
            st.metric("Produtos com Estoque Baixo", len(df_baixo_estoque))
            st.dataframe(df_baixo_estoque, use_container_width=True)
        else:
            st.info("📝 Nenhum produto cadastrado")

# =========================================
# 🔐 MODAL PARA ALTERAR SENHA DE USUÁRIO (ADMIN)
# =========================================

if st.session_state.get('alterar_senha_usuario'):
    with st.container():
        st.markdown(f"<h3>🔐 Alterar Senha de {st.session_state.nome_usuario}</h3>", unsafe_allow_html=True)
        
        nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha_usuario_input")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha_usuario_input")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Salvar Nova Senha", use_container_width=True, key="salvar_senha_usuario"):
                if nova_senha and confirmar_senha:
                    if nova_senha == confirmar_senha:
                        success, msg = alterar_senha(st.session_state.alterar_senha_usuario, nova_senha)
                        if success:
                            st.success(msg)
                            st.session_state.alterar_senha_usuario = None
                            st.session_state.nome_usuario = None
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ As senhas não coincidem!")
                else:
                    st.error("❌ Preencha todos os campos!")
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True, key="cancelar_senha_usuario"):
                st.session_state.alterar_senha_usuario = None
                st.session_state.nome_usuario = None
                st.rerun()

# =========================================
# 🎯 RODAPÉ
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("👕 **FashionManager Pro**")
st.sidebar.markdown("v4.0 • Sistema Completo")

# Verificar se está rodando no Render
if os.environ.get('DATABASE_URL'):
    st.sidebar.success("🌐 Modo: PostgreSQL (Render)")
else:
    st.sidebar.info("💻 Modo: SQLite (Local)")
