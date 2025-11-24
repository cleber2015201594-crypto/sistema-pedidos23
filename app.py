import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse as urlparse

# =========================================
# 🎯 CONFIGURAÇÃO PARA MOBILE
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar recolhida no mobile
)

# CSS para otimização mobile
st.markdown("""
<style>
    /* Otimização para mobile */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        /* Botões maiores para mobile */
        .stButton button {
            width: 100%;
            padding: 0.75rem;
            font-size: 1.1rem;
        }
        
        /* Inputs maiores */
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px !important; /* Previne zoom no iOS */
            padding: 0.75rem !important;
        }
        
        /* Tabelas responsivas */
        .dataframe {
            font-size: 12px;
        }
        
        /* Sidebar compacta */
        .css-1d391kg {
            padding: 1rem;
        }
    }
    
    /* Melhorias gerais */
    .compact-text {
        font-size: 0.9rem;
    }
    
    .mobile-hidden {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO AVANÇADO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def atualizar_estrutura_banco():
    """Atualiza a estrutura do banco se necessário"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Verificar se a coluna escola_id existe na tabela produtos
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='produtos' and column_name='escola_id'
        """)
        resultado = cur.fetchone()
        
        if not resultado:
            cur.execute('ALTER TABLE produtos ADD COLUMN escola_id INTEGER REFERENCES escolas(id)')
            st.success("✅ Estrutura atualizada")
        
        # Verificar forma_pagamento
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='pedidos' and column_name='forma_pagamento'
        """)
        resultado = cur.fetchone()
        
        if not resultado:
            cur.execute('ALTER TABLE pedidos ADD COLUMN forma_pagamento VARCHAR(50) DEFAULT \'Dinheiro\'')
            st.success("✅ Forma pagamento adicionada")
        
        # Verificar data_entrega_real
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='pedidos' and column_name='data_entrega_real'
        """)
        resultado = cur.fetchone()
        
        if not resultado:
            cur.execute('ALTER TABLE pedidos ADD COLUMN data_entrega_real DATE')
            st.success("✅ Data entrega real adicionada")
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro estrutura banco: {str(e)}")
        return False
    finally:
        conn.close()

def init_db():
    """Inicializa o banco de dados"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    nome_completo VARCHAR(100),
                    tipo VARCHAR(20) DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT TRUE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(200) NOT NULL,
                    categoria VARCHAR(100),
                    tamanho VARCHAR(10),
                    cor VARCHAR(50),
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    descricao TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER REFERENCES clientes(id),
                    status VARCHAR(50) DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    quantidade_total INTEGER,
                    valor_total DECIMAL(10,2),
                    observacoes TEXT
                )
            ''')
            
            # Tabela de itens do pedido
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_itens (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario DECIMAL(10,2),
                    subtotal DECIMAL(10,2)
                )
            ''')
            
            # Usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                cur.execute('''
                    INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                ''', (username, password_hash, nome, tipo))
            
            # Escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                cur.execute('''
                    INSERT INTO escolas (nome) VALUES (%s)
                    ON CONFLICT (nome) DO NOTHING
                ''', (escola,))
            
            conn.commit()
            atualizar_estrutura_banco()
            
        except Exception as e:
            st.error(f"Erro init db: {str(e)}")
        finally:
            conn.close()

def get_connection():
    """Estabelece conexão com PostgreSQL"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        else:
            st.error("DATABASE_URL não configurada")
            return None
            
    except Exception as e:
        st.error(f"Erro conexão: {str(e)}")
        return None

def verificar_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro conexão"
    
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
# 📱 SISTEMA DE LOGIN MOBILE-FRIENDLY
# =========================================

def login():
    """Interface de login otimizada para mobile"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>👕 Sistema Fardamentos</h1>
        <p>Faça login para continuar</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        
        submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
        
        if submitted:
            if username and password:
                with st.spinner("Verificando..."):
                    sucesso, mensagem, tipo_usuario = verificar_login(username, password)
                    if sucesso:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.nome_usuario = mensagem
                        st.session_state.tipo_usuario = tipo_usuario
                        st.success(f"Bem-vindo, {mensagem}!")
                        st.rerun()
                    else:
                        st.error(mensagem)
            else:
                st.error("Preencha todos os campos")

# =========================================
# 🗃️ FUNÇÕES DO BANCO DE DADOS
# =========================================

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (%s, %s, %s, %s) RETURNING id",
            (nome, telefone, email, data_cadastro)
        )
        
        conn.commit()
        return True, "Cliente cadastrado!"
        
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
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro listar clientes: {e}")
        return []
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro conexão"
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='produtos' and column_name='escola_id'
        """)
        tem_escola_id = cur.fetchone()
        
        if tem_escola_id:
            cur.execute('''
                INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        else:
            cur.execute('''
                INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (nome, categoria, tamanho, cor, preco, estoque, descricao))
        
        conn.commit()
        return True, "Produto cadastrado!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='produtos' and column_name='escola_id'
        """)
        tem_escola_id = cur.fetchone()
        
        if tem_escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY p.nome
            ''')
        else:
            cur.execute('SELECT p.*, NULL as escola_nome FROM produtos p ORDER BY p.nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro listar produtos: {e}")
        return []
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
    except Exception as e:
        st.error(f"Erro listar escolas: {e}")
        return []
    finally:
        conn.close()

def adicionar_pedido(cliente_id, itens, data_entrega, forma_pagamento, observacoes):
    conn = get_connection()
    if not conn:
        return False, "Erro conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='pedidos' and column_name='forma_pagamento'
        """)
        tem_forma_pagamento = cur.fetchone()
        
        if tem_forma_pagamento:
            cur.execute('''
                INSERT INTO pedidos (cliente_id, data_entrega_prevista, forma_pagamento, quantidade_total, valor_total, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            ''', (cliente_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes))
        else:
            cur.execute('''
                INSERT INTO pedidos (cliente_id, data_entrega_prevista, quantidade_total, valor_total, observacoes)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (cliente_id, data_entrega, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.fetchone()[0]
        
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            # Atualizar estoque
            cur.execute("UPDATE produtos SET estoque = estoque - %s WHERE id = %s", 
                       (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.data_pedido DESC
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro listar pedidos: {e}")
        return []
    finally:
        conn.close()

# =========================================
# 📱 INTERFACE PRINCIPAL MOBILE
# =========================================

# Inicialização
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# Menu mobile-friendly
st.sidebar.markdown(f"**👤 {st.session_state.nome_usuario}**")
st.sidebar.markdown(f"**🎯 {st.session_state.tipo_usuario}**")

# Menu principal com ícones
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header responsivo
st.markdown(f"""
<div style='text-align: center; padding: 1rem 0;'>
    <h2>{menu}</h2>
</div>
""", unsafe_allow_html=True)

# =========================================
# 📱 PÁGINAS MOBILE-OPTIMIZED
# =========================================

if menu == "📊 Dashboard":
    col1, col2 = st.columns(2)
    
    with col1:
        pedidos = listar_pedidos()
        st.metric("📦 Pedidos", len(pedidos))
    
    with col2:
        clientes = listar_clientes()
        st.metric("👥 Clientes", len(clientes))
    
    # Ações rápidas
    st.subheader("⚡ Ações Rápidas")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Listar"])
    
    with tab1:
        with st.form("novo_cliente"):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True):
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")
    
    with tab2:
        clientes = listar_clientes()
        if clientes:
            for cliente in clientes:
                with st.expander(f"👤 {cliente[1]}"):
                    st.write(f"📞 {cliente[2] or 'N/A'}")
                    st.write(f"📧 {cliente[3] or 'N/A'}")
                    st.write(f"📅 {cliente[4]}")
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Listar"])
    
    with tab1:
        with st.form("novo_produto"):
            nome = st.text_input("Nome do produto*")
            categoria = st.selectbox("Categoria", ["Camisetas", "Calças/Shorts", "Agasalhos"])
            tamanho = st.selectbox("Tamanho", ["2", "4", "6", "8", "10", "12", "PP", "P", "M", "G", "GG"])
            cor = st.text_input("Cor", value="Branco")
            preco = st.number_input("Preço (R$)", min_value=0.0, value=29.90)
            estoque = st.number_input("Estoque inicial", min_value=0, value=10)
            descricao = st.text_area("Descrição")
            
            escolas_db = listar_escolas()
            escola_selecionada = st.selectbox("🏫 Escola", [e[1] for e in escolas_db])
            
            if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True):
                if nome and escola_selecionada:
                    escola_id = next(e[0] for e in escolas_db if e[1] == escola_selecionada)
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome e escola são obrigatórios!")
    
    with tab2:
        produtos = listar_produtos()
        if produtos:
            for produto in produtos:
                with st.expander(f"👕 {produto[1]} - {produto[3]} - {produto[4]}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Categoria:** {produto[2]}")
                        st.write(f"**Preço:** R$ {produto[5]:.2f}")
                    with col2:
                        st.write(f"**Estoque:** {produto[6]}")
                        st.write(f"**Escola:** {produto[9] or 'N/A'}")
        else:
            st.info("👕 Nenhum produto cadastrado")

elif menu == "📦 Pedidos":
    tab1, tab2 = st.tabs(["➕ Novo Pedido", "📋 Meus Pedidos"])
    
    with tab1:
        clientes = listar_clientes()
        if clientes:
            cliente_selecionado = st.selectbox(
                "Selecione o cliente:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                produtos = listar_produtos()
                if produtos:
                    # Adicionar itens
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        produto_selecionado = st.selectbox(
                            "Produto:",
                            [f"{p[1]} - {p[3]} - {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" for p in produtos]
                        )
                    with col2:
                        quantidade = st.number_input("Qtd", min_value=1, value=1)
                    
                    if st.button("➕ Adicionar Item", use_container_width=True):
                        if 'itens_pedido' not in st.session_state:
                            st.session_state.itens_pedido = []
                        
                        produto_id = next(p[0] for p in produtos if f"{p[1]} - {p[3]} - {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" == produto_selecionado)
                        produto = next(p for p in produtos if p[0] == produto_id)
                        
                        if quantidade > produto[6]:
                            st.error("❌ Estoque insuficiente!")
                        else:
                            item = {
                                'produto_id': produto_id,
                                'nome': produto[1],
                                'quantidade': quantidade,
                                'preco_unitario': float(produto[5]),
                                'subtotal': float(produto[5]) * quantidade
                            }
                            st.session_state.itens_pedido.append(item)
                            st.success("✅ Item adicionado!")
                            st.rerun()
                    
                    # Itens do pedido
                    if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
                        st.subheader("📋 Itens do Pedido")
                        total = 0
                        
                        for i, item in enumerate(st.session_state.itens_pedido):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"**{item['nome']}**")
                            with col2:
                                st.write(f"Qtd: {item['quantidade']}")
                            with col3:
                                st.write(f"R$ {item['subtotal']:.2f}")
                                if st.button("❌", key=f"del_{i}"):
                                    st.session_state.itens_pedido.pop(i)
                                    st.rerun()
                            total += item['subtotal']
                        
                        st.write(f"**Total: R$ {total:.2f}**")
                        
                        # Finalizar pedido
                        data_entrega = st.date_input("📅 Entrega Prevista", min_value=date.today())
                        forma_pagamento = st.selectbox("💳 Pagamento", ["Dinheiro", "Cartão", "PIX"])
                        observacoes = st.text_area("Observações")
                        
                        if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                            sucesso, resultado = adicionar_pedido(
                                cliente_id, 
                                st.session_state.itens_pedido, 
                                data_entrega, 
                                forma_pagamento,
                                observacoes
                            )
                            if sucesso:
                                st.success(f"✅ Pedido #{resultado} criado!")
                                del st.session_state.itens_pedido
                                st.rerun()
                            else:
                                st.error(f"❌ Erro: {resultado}")
                else:
                    st.error("❌ Nenhum produto cadastrado")
        else:
            st.error("❌ Nenhum cliente cadastrado")
    
    with tab2:
        pedidos = listar_pedidos()
        if pedidos:
            for pedido in pedidos:
                status_cor = {
                    'Pendente': '🟡',
                    'Em produção': '🟠',
                    'Pronto para entrega': '🔵',
                    'Entregue': '🟢',
                    'Cancelado': '🔴'
                }.get(pedido[2], '⚪')
                
                with st.expander(f"{status_cor} Pedido #{pedido[0]} - {pedido[9]}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Status:** {pedido[2]}")
                        st.write(f"**Data:** {pedido[4]}")
                    with col2:
                        st.write(f"**Valor:** R$ {float(pedido[8]):.2f}")
                        st.write(f"**Entrega:** {pedido[5]}")
        else:
            st.info("📦 Nenhum pedido realizado")

elif menu == "📦 Estoque":
    produtos = listar_produtos()
    if produtos:
        for produto in produtos:
            with st.expander(f"👕 {produto[1]} - Estoque: {produto[6]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Tamanho:** {produto[3]}")
                    st.write(f"**Cor:** {produto[4]}")
                with col2:
                    st.write(f"**Preço:** R$ {produto[5]:.2f}")
                    st.write(f"**Escola:** {produto[9] or 'N/A'}")
                
                # Ajuste rápido de estoque
                novo_estoque = st.number_input(
                    "Novo estoque", 
                    min_value=0, 
                    value=produto[6],
                    key=f"estoque_{produto[0]}"
                )
                
                if novo_estoque != produto[6]:
                    if st.button("💾 Atualizar", key=f"btn_{produto[0]}", use_container_width=True):
                        conn = get_connection()
                        if conn:
                            try:
                                cur = conn.cursor()
                                cur.execute("UPDATE produtos SET estoque = %s WHERE id = %s", (novo_estoque, produto[0]))
                                conn.commit()
                                st.success("✅ Estoque atualizado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {str(e)}")
                            finally:
                                conn.close()
    else:
        st.info("👕 Nenhum produto cadastrado")

# Logout na sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Rodapé
st.sidebar.markdown("---")
st.sidebar.markdown("👕 **Sistema Fardamentos v2.0**", help="Sistema otimizado para mobile")
