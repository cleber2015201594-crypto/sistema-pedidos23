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
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            
            # Tabela de itens do pedido
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_itens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario REAL,
                    subtotal REAL
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

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    try:
        cur = conn.cursor()
        cur.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (nova_quantidade, produto_id))
        conn.commit()
        return True, "Estoque atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def adicionar_pedido(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        # Verificar estoque (apenas alerta, não bloqueia)
        alertas_estoque = []
        for item in itens:
            cur.execute("SELECT estoque, nome FROM produtos WHERE id = ?", (item['produto_id'],))
            produto = cur.fetchone()
            if produto and produto[0] < item['quantidade']:
                alertas_estoque.append(f"{produto[1]} - Estoque: {produto[0]}, Pedido: {item['quantidade']}")
        
        # Criar pedido
        cur.execute('''
            INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, quantidade_total, valor_total, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.lastrowid
        
        # Inserir itens do pedido
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
        
        conn.commit()
        
        mensagem = f"✅ Pedido #{pedido_id} criado com sucesso!"
        if alertas_estoque:
            mensagem += f" ⚠️ Alertas de estoque: {', '.join(alertas_estoque)}"
            
        return True, mensagem
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.escola_id = ?
                ORDER BY p.data_pedido DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                ORDER BY p.data_pedido DESC
            ''')
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def atualizar_status_pedido(pedido_id, novo_status):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        if novo_status == 'Entregue':
            data_entrega = datetime.now().strftime("%Y-%m-%d")
            cur.execute('UPDATE pedidos SET status = ?, data_entrega_real = ? WHERE id = ?', (novo_status, data_entrega, pedido_id))
        else:
            cur.execute('UPDATE pedidos SET status = ? WHERE id = ?', (novo_status, pedido_id))
            
        conn.commit()
        return True, "✅ Status do pedido atualizado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()
        return True, "Pedido excluído com sucesso"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def baixar_estoque_pedido(pedido_id):
    """Baixa o estoque quando o pedido é marcado como entregue"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Buscar itens do pedido
        cur.execute('''
            SELECT pi.produto_id, pi.quantidade 
            FROM pedido_itens pi 
            WHERE pi.pedido_id = ?
        ''', (pedido_id,))
        itens = cur.fetchall()
        
        # Baixar estoque
        for item in itens:
            produto_id, quantidade = item
            cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id))
        
        conn.commit()
        return True, "✅ Estoque baixado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao baixar estoque: {str(e)}"
    finally:
        conn.close()

def gerar_relatorio_vendas_por_escola(escola_id=None):
    """Gera relatório de vendas por período e escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_vendas
                FROM pedidos p
                WHERE p.escola_id = ? AND p.status != 'Cancelado'
                GROUP BY DATE(p.data_pedido)
                ORDER BY data DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    e.nome as escola,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_vendas
                FROM pedidos p
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.status != 'Cancelado'
                GROUP BY DATE(p.data_pedido), e.nome
                ORDER BY data DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Data', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Data', 'Escola', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            
            # Formatar data no padrão brasileiro
            df['Data'] = df['Data'].apply(formatar_data_brasil)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_produtos_por_escola(escola_id=None):
    """Gera relatório de produtos mais vendidos por escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    pr.nome as produto,
                    pr.categoria,
                    pr.tamanho,
                    pr.cor,
                    SUM(pi.quantidade) as total_vendido,
                    SUM(pi.subtotal) as total_faturado
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                JOIN pedidos p ON pi.pedido_id = p.id
                WHERE p.escola_id = ? AND p.status != 'Cancelado'
                GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor
                ORDER BY total_vendido DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    pr.nome as produto,
                    pr.categoria,
                    pr.tamanho,
                    pr.cor,
                    e.nome as escola,
                    SUM(pi.quantidade) as total_vendido,
                    SUM(pi.subtotal) as total_faturado
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                JOIN pedidos p ON pi.pedido_id = p.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.status != 'Cancelado'
                GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor, e.nome
                ORDER BY total_vendido DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Total Vendido', 'Total Faturado (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Escola', 'Total Vendido', 'Total Faturado (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
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
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

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
                    with col2:
                        # Edição de estoque
                        novo_estoque = st.number_input("Estoque:", value=produto['estoque'], min_value=0, key=f"estoque_{produto['id']}")
                        if st.button("💾 Atualizar", key=f"btn_{produto['id']}"):
                            if novo_estoque != produto['estoque']:
                                sucesso, msg = atualizar_estoque(produto['id'], novo_estoque)
                                if sucesso:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
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
                
                # Lista de produtos com ajuste de estoque
                for produto in produtos:
                    status_estoque = "✅" if produto['estoque'] >= 10 else "⚠️" if produto['estoque'] >= 5 else "❌"
                    
                    with st.expander(f"{status_estoque} {produto['nome']} - {produto['tamanho']} - {produto['cor']}"):
                        col1, col2 = st.columns([3,1])
                        with col1:
                            st.write(f"**Categoria:** {produto['categoria']}")
                            st.write(f"**Preço:** R$ {produto['preco']:.2f}")
                            st.write(f"**Estoque Atual:** {produto['estoque']} unidades")
                            st.write(f"**Descrição:** {produto['descricao'] or 'Sem descrição'}")
                        with col2:
                            novo_estoque = st.number_input(
                                "Novo estoque:",
                                min_value=0,
                                value=produto['estoque'],
                                key=f"estoque_{produto['id']}_{idx}"
                            )
                            if st.button("💾 Atualizar", key=f"btn_{produto['id']}_{idx}"):
                                if novo_estoque != produto['estoque']:
                                    sucesso, msg = atualizar_estoque(produto['id'], novo_estoque)
                                    if sucesso:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
            else:
                st.info(f"📭 Nenhum produto cadastrado para {escola['nome']}")

elif menu == "📦 Pedidos":
    st.header("📦 Gestão de Pedidos")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🆕 Novo Pedido", "📋 Pedidos em Andamento", "✅ Pedidos Entregues", "❌ Pedidos Cancelados"])
    
    with tab1:
        st.subheader("🆕 Criar Novo Pedido")
        
        # Seleção da escola
        escola_nome = st.selectbox("🏫 Escola:", [e['nome'] for e in escolas], key="nova_escola_pedido")
        escola_id = next(e['id'] for e in escolas if e['nome'] == escola_nome)
        
        # Seleção do cliente
        clientes = listar_clientes()
        if not clientes:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
        else:
            cliente_opcoes = [f"{c['nome']} (ID: {c['id']})" for c in clientes]
            cliente_selecionado = st.selectbox("👤 Cliente:", cliente_opcoes)
            cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
            
            # Adicionar itens
            st.subheader("🛒 Itens do Pedido")
            produtos = listar_produtos_por_escola(escola_id)
            
            if not produtos:
                st.error(f"❌ Nenhum produto cadastrado para {escola_nome}. Cadastre produtos primeiro.")
            else:
                # Interface para adicionar itens
                if 'itens_pedido' not in st.session_state:
                    st.session_state.itens_pedido = []
                
                col1, col2, col3, col4 = st.columns([3,1,1,1])
                with col1:
                    produto_opcoes = [f"{p['nome']} | T: {p['tamanho']} | C: {p['cor']} | Est: {p['estoque']} | R$ {p['preco']:.2f}" for p in produtos]
                    produto_sel = st.selectbox("Produto:", produto_opcoes)
                with col2:
                    qtd = st.number_input("Qtd:", min_value=1, value=1)
                with col3:
                    preco_unit = next(p['preco'] for p in produtos if f"{p['nome']} | T: {p['tamanho']} | C: {p['cor']} | Est: {p['estoque']} | R$ {p['preco']:.2f}" == produto_sel)
                    st.write(f"R$ {preco_unit:.2f}")
                with col4:
                    if st.button("➕ Add", use_container_width=True):
                        produto_id = next(p['id'] for p in produtos if f"{p['nome']} | T: {p['tamanho']} | C: {p['cor']} | Est: {p['estoque']} | R$ {p['preco']:.2f}" == produto_sel)
                        
                        item = {
                            'produto_id': produto_id,
                            'nome': next(p['nome'] for p in produtos if p['id'] == produto_id),
                            'tamanho': next(p['tamanho'] for p in produtos if p['id'] == produto_id),
                            'cor': next(p['cor'] for p in produtos if p['id'] == produto_id),
                            'quantidade': qtd,
                            'preco_unitario': preco_unit,
                            'subtotal': preco_unit * qtd
                        }
                        st.session_state.itens_pedido.append(item)
                        st.success("✅ Item adicionado!")
                        st.rerun()
                
                # Mostrar itens do pedido
                if st.session_state.itens_pedido:
                    st.subheader("📋 Resumo do Pedido")
                    total = 0
                    
                    for i, item in enumerate(st.session_state.itens_pedido):
                        col1, col2, col3, col4, col5 = st.columns([3,1,1,1,1])
                        with col1:
                            st.write(f"**{item['nome']}**")
                            st.write(f"{item['tamanho']} | {item['cor']}")
                        with col2:
                            st.write(f"Qtd: {item['quantidade']}")
                        with col3:
                            st.write(f"R$ {item['preco_unitario']:.2f}")
                        with col4:
                            st.write(f"R$ {item['subtotal']:.2f}")
                        with col5:
                            if st.button("❌", key=f"del_{i}"):
                                st.session_state.itens_pedido.pop(i)
                                st.rerun()
                        
                        total += item['subtotal']
                    
                    st.success(f"**💰 Total do Pedido: R$ {total:.2f}**")
                    
                    # Informações finais do pedido
                    col1, col2 = st.columns(2)
                    with col1:
                        data_entrega = st.date_input("📅 Previsão de Entrega", min_value=date.today())
                        forma_pagamento = st.selectbox("💳 Pagamento:", ["Dinheiro", "Cartão", "PIX", "Transferência"])
                    with col2:
                        observacoes = st.text_area("📝 Observações")
                    
                    if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                        if st.session_state.itens_pedido:
                            sucesso, resultado = adicionar_pedido(
                                cliente_id, escola_id, st.session_state.itens_pedido, 
                                data_entrega, forma_pagamento, observacoes
                            )
                            if sucesso:
                                st.success(f"✅ {resultado}")
                                del st.session_state.itens_pedido
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ {resultado}")
                        else:
                            st.error("❌ Adicione pelo menos um item ao pedido!")
                else:
                    st.info("🛒 Adicione itens ao pedido usando o botão 'Adicionar Item'")
    
    with tab2:
        st.subheader("📋 Pedidos em Andamento")
        pedidos = listar_pedidos_por_escola()
        
        if pedidos:
            # Filtrar apenas pedidos não entregues e não cancelados
            pedidos_em_andamento = [p for p in pedidos if p['status'] not in ['Entregue', 'Cancelado']]
            
            if pedidos_em_andamento:
                for pedido in pedidos_em_andamento:
                    status_icon = {
                        'Pendente': '🟡',
                        'Em produção': '🟠', 
                        'Pronto para entrega': '🔵'
                    }.get(pedido['status'], '⚪')
                    
                    with st.expander(f"{status_icon} Pedido #{pedido['id']} - {pedido['cliente_nome']} - {pedido['escola_nome']} - R$ {pedido['valor_total']:.2f} - {pedido['status']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Cliente:** {pedido['cliente_nome']}")
                            st.write(f"**Escola:** {pedido['escola_nome']}")
                            st.write(f"**Data do Pedido:** {formatar_data_brasil(pedido['data_pedido'])}")
                            st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        
                        with col2:
                            st.write(f"**Forma de Pagamento:** {pedido['forma_pagamento']}")
                            st.write(f"**Quantidade Total:** {pedido['quantidade_total']}")
                            st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                            if pedido['observacoes']:
                                st.write(f"**Observações:** {pedido['observacoes']}")
                        
                        # Alterar status do pedido
                        st.subheader("🔄 Alterar Status do Pedido")
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            novo_status = st.selectbox(
                                "Novo status:",
                                ["Pendente", "Em produção", "Pronto para entrega", "Entregue", "Cancelado"],
                                key=f"status_{pedido['id']}"
                            )
                        with col2:
                            if st.button("🔄 Atualizar", key=f"upd_{pedido['id']}"):
                                if novo_status != pedido['status']:
                                    sucesso, msg = atualizar_status_pedido(pedido['id'], novo_status)
                                    if sucesso:
                                        if novo_status == 'Entregue':
                                            # Baixar estoque quando o pedido é marcado como entregue
                                            sucesso_estoque, msg_estoque = baixar_estoque_pedido(pedido['id'])
                                            if sucesso_estoque:
                                                st.success(f"{msg} {msg_estoque}")
                                            else:
                                                st.error(f"{msg} Mas {msg_estoque}")
                                        else:
                                            st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with col3:
                            if st.button("🗑️ Excluir Pedido", key=f"del_{pedido['id']}"):
                                st.warning("⚠️ Esta ação não pode ser desfeita!")
                                if st.button("✅ Confirmar Exclusão", key=f"conf_del_{pedido['id']}"):
                                    sucesso, msg = excluir_pedido(pedido['id'])
                                    if sucesso:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
            else:
                st.info("📦 Nenhum pedido em andamento")
        else:
            st.info("📦 Nenhum pedido realizado")
    
    with tab3:
        st.subheader("✅ Pedidos Entregues")
        pedidos = listar_pedidos_por_escola()
        
        if pedidos:
            # Filtrar apenas pedidos entregues
            pedidos_entregues = [p for p in pedidos if p['status'] == 'Entregue']
            
            if pedidos_entregues:
                for pedido in pedidos_entregues:
                    with st.expander(f"✅ Pedido #{pedido['id']} - {pedido['cliente_nome']} - {pedido['escola_nome']} - R$ {pedido['valor_total']:.2f}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Cliente:** {pedido['cliente_nome']}")
                            st.write(f"**Escola:** {pedido['escola_nome']}")
                            st.write(f"**Data do Pedido:** {formatar_data_brasil(pedido['data_pedido'])}")
                            st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                            st.write(f"**Entregue em:** {formatar_data_brasil(pedido['data_entrega_real'])}")
                        
                        with col2:
                            st.write(f"**Forma de Pagamento:** {pedido['forma_pagamento']}")
                            st.write(f"**Quantidade Total:** {pedido['quantidade_total']}")
                            st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                            if pedido['observacoes']:
                                st.write(f"**Observações:** {pedido['observacoes']}")
            else:
                st.info("✅ Nenhum pedido entregue")
        else:
            st.info("📦 Nenhum pedido realizado")
    
    with tab4:
        st.subheader("❌ Pedidos Cancelados")
        pedidos = listar_pedidos_por_escola()
        
        if pedidos:
            # Filtrar apenas pedidos cancelados
            pedidos_cancelados = [p for p in pedidos if p['status'] == 'Cancelado']
            
            if pedidos_cancelados:
                for pedido in pedidos_cancelados:
                    with st.expander(f"❌ Pedido #{pedido['id']} - {pedido['cliente_nome']} - {pedido['escola_nome']} - R$ {pedido['valor_total']:.2f}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Cliente:** {pedido['cliente_nome']}")
                            st.write(f"**Escola:** {pedido['escola_nome']}")
                            st.write(f"**Data do Pedido:** {formatar_data_brasil(pedido['data_pedido'])}")
                            st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        
                        with col2:
                            st.write(f"**Forma de Pagamento:** {pedido['forma_pagamento']}")
                            st.write(f"**Quantidade Total:** {pedido['quantidade_total']}")
                            st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                            if pedido['observacoes']:
                                st.write(f"**Observações:** {pedido['observacoes']}")
                        
                        # Opção para reativar pedido cancelado
                        if st.button("🔄 Reativar Pedido", key=f"reativar_{pedido['id']}"):
                            sucesso, msg = atualizar_status_pedido(pedido['id'], "Pendente")
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
            else:
                st.info("❌ Nenhum pedido cancelado")
        else:
            st.info("📦 Nenhum pedido realizado")

elif menu == "📈 Relatórios":
    st.header("📈 Relatórios e Estatísticas")
    
    escolas = listar_escolas()
    
    tab1, tab2 = st.tabs(["📊 Vendas por Escola", "📦 Produtos Mais Vendidos"])
    
    with tab1:
        st.subheader("📊 Relatório de Vendas por Escola")
        
        escola_relatorio = st.selectbox(
            "Selecione a escola:",
            ["Todas as escolas"] + [e['nome'] for e in escolas],
            key="relatorio_escola"
        )
        
        if escola_relatorio == "Todas as escolas":
            relatorio_vendas = gerar_relatorio_vendas_por_escola()
        else:
            escola_id = next(e['id'] for e in escolas if e['nome'] == escola_relatorio)
            relatorio_vendas = gerar_relatorio_vendas_por_escola(escola_id)
        
        if not relatorio_vendas.empty:
            st.dataframe(relatorio_vendas, use_container_width=True)
            
            # Gráfico de vendas
            if escola_relatorio == "Todas as escolas":
                fig = px.line(relatorio_vendas, x='Data', y='Total Vendas (R$)', color='Escola',
                             title='Evolução das Vendas por Escola')
            else:
                fig = px.line(relatorio_vendas, x='Data', y='Total Vendas (R$)', 
                             title=f'Evolução das Vendas - {escola_relatorio}')
            st.plotly_chart(fig, use_container_width=True)
            
            # Métricas resumidas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Período", f"R$ {relatorio_vendas['Total Vendas (R$)'].sum():.2f}")
            with col2:
                st.metric("Média Diária", f"R$ {relatorio_vendas['Total Vendas (R$)'].mean():.2f}")
            with col3:
                st.metric("Maior Venda", f"R$ {relatorio_vendas['Total Vendas (R$)'].max():.2f}")
        else:
            st.info("📊 Nenhum dado de venda disponível")
    
    with tab2:
        st.subheader("📦 Produtos Mais Vendidos")
        
        escola_produtos = st.selectbox(
            "Selecione a escola:",
            ["Todas as escolas"] + [e['nome'] for e in escolas],
            key="produtos_relatorio"
        )
        
        if escola_produtos == "Todas as escolas":
            relatorio_produtos = gerar_relatorio_produtos_por_escola()
        else:
            escola_id = next(e['id'] for e in escolas if e['nome'] == escola_produtos)
            relatorio_produtos = gerar_relatorio_produtos_por_escola(escola_id)
        
        if not relatorio_produtos.empty:
            st.dataframe(relatorio_produtos, use_container_width=True)
            
            # Gráfico de produtos mais vendidos
            top_produtos = relatorio_produtos.head(10)
            if escola_produtos == "Todas as escolas":
                fig = px.bar(top_produtos, x='Produto', y='Total Vendido', color='Escola',
                            title='Top 10 Produtos Mais Vendidos')
            else:
                fig = px.bar(top_produtos, x='Produto', y='Total Vendido',
                            title=f'Top 10 Produtos Mais Vendidos - {escola_produtos}')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📦 Nenhum dado de produto vendido disponível")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v2.0\n\nDesenvolvido para gestão escolar")

# Botão para recarregar
if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()