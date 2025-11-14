import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import urllib.parse as urlparse

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

@st.cache_resource
def get_connection():
    """Conecta com PostgreSQL no Render"""
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        
        if not DATABASE_URL:
            st.error("❌ DATABASE_URL não encontrada")
            return None
            
        # Converte postgres:// para postgresql://
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
            
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
        
    except Exception as e:
        st.error(f"❌ Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa tabelas no banco"""
    conn = get_connection()
    if not conn:
        return False
        
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
                cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
                escola_id INTEGER REFERENCES escolas(id) ON DELETE CASCADE,
                UNIQUE(cliente_id, escola_id)
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
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabela de pedidos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER REFERENCES clientes(id),
                escola_id INTEGER REFERENCES escolas(id),
                status VARCHAR(50) DEFAULT 'Pendente',
                data_pedido DATE DEFAULT CURRENT_DATE,
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
        
        # Inserir escolas padrão
        escolas = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas:
            cur.execute(
                "INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING",
                (escola,)
            )
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Inicializar banco na primeira execução
if 'db_init' not in st.session_state:
    if init_db():
        st.session_state.db_init = True

# =========================================
# 🔧 FUNÇÕES PRINCIPAIS
# =========================================

def adicionar_cliente(nome, telefone, email, escolas_ids):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão com o banco"
    
    try:
        cur = conn.cursor()
        
        # Inserir cliente
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s) RETURNING id",
            (nome, telefone, email)
        )
        cliente_id = cur.fetchone()[0]
        
        # Inserir relações com escolas
        for escola_id in escolas_ids:
            cur.execute(
                "INSERT INTO cliente_escolas (cliente_id, escola_id) VALUES (%s, %s)",
                (cliente_id, escola_id)
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
        cur.execute('''
            SELECT c.*, string_agg(e.nome, ', ') as escolas
            FROM clientes c
            LEFT JOIN cliente_escolas ce ON c.id = ce.cliente_id
            LEFT JOIN escolas e ON ce.escola_id = e.id
            GROUP BY c.id
            ORDER BY c.nome
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão com o banco"
    
    try:
        cur = conn.cursor()
        
        # Verificar se tem pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = %s", (cliente_id,))
        if cur.fetchone()[0] > 0:
            return False, "❌ Cliente possui pedidos e não pode ser excluído"
        
        # Excluir cliente (as relações serão excluídas automaticamente por CASCADE)
        cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        
        conn.commit()
        return True, "✅ Cliente excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
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
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (nome, categoria, tamanho, cor, preco, estoque, descricao))
        
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM produtos ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
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
    ["📊 Dashboard", "👥 Clientes", "👕 Produtos", "📦 Pedidos", "📈 Relatórios"])

st.sidebar.markdown("---")
st.sidebar.write(f"👤 Usuário: **{st.session_state.username}**")

if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Sistema de Fardamentos")
    
    # Verificar conexão com banco
    conn = get_connection()
    if conn:
        st.success("✅ **Conectado ao PostgreSQL no Render!**")
        conn.close()
    else:
        st.error("❌ **Erro na conexão com o banco**")
    
    # Métricas
    clientes = listar_clientes()
    produtos = listar_produtos()
    escolas = listar_escolas()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Clientes", len(clientes))
    
    with col2:
        st.metric("👕 Total Produtos", len(produtos))
    
    with col3:
        st.metric("🏫 Escolas", len(escolas))
    
    with col4:
        baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("⚠️ Alertas Estoque", baixo_estoque)
    
    # Ações rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col2:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col3:
        if st.button("📦 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()

elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.header("➕ Cadastrar Novo Cliente")
        
        with st.form("form_cliente"):
            nome = st.text_input("👤 Nome completo*", placeholder="Digite o nome completo")
            telefone = st.text_input("📞 Telefone", placeholder="(11) 99999-9999")
            email = st.text_input("📧 Email", placeholder="cliente@email.com")
            
            escolas_db = listar_escolas()
            if escolas_db:
                escolas_opcoes = [e[1] for e in escolas_db]
                escolas_selecionadas = st.multiselect(
                    "🏫 Escolas do cliente*",
                    options=escolas_opcoes,
                    help="Selecione todas as escolas que o cliente frequenta"
                )
            else:
                st.error("Nenhuma escola cadastrada no sistema")
                escolas_selecionadas = []
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente", type="primary")
            
            if submitted:
                if nome and escolas_selecionadas:
                    escolas_ids = [e[0] for e in escolas_db if e[1] in escolas_selecionadas]
                    sucesso, msg = adicionar_cliente(nome, telefone, email, escolas_ids)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome e pelo menos uma escola são obrigatórios!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
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
            
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Estatísticas
            st.subheader("📊 Estatísticas")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Clientes", len(clientes))
            with col2:
                total_escolas = df['Escolas'].str.split(', ').explode().nunique()
                st.metric("Escolas Ativas", total_escolas)
        else:
            st.info("📭 Nenhum cliente cadastrado no sistema")
    
    with tab3:
        st.header("🗑️ Excluir Cliente")
        clientes = listar_clientes()
        
        if clientes:
            cliente_opcoes = [f"{c[1]} (ID: {c[0]}) - Escolas: {c[4] or 'Nenhuma'}" for c in clientes]
            cliente_selecionado = st.selectbox(
                "Selecione o cliente para excluir:",
                options=cliente_opcoes,
                key="excluir_cliente"
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].split(")")[0])
                
                st.warning("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
                st.info("📋 **Restrição:** Clientes com pedidos ativos não podem ser excluídos")
                
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, msg = excluir_cliente(cliente_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("📭 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    st.title("👕 Gestão de Produtos")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Listar Produtos"])
    
    with tab1:
        st.header("➕ Cadastrar Novo Produto")
        
        with st.form("form_produto"):
            nome = st.text_input("Nome do produto*", placeholder="Ex: Camiseta Básica")
            
            col1, col2 = st.columns(2)
            with col1:
                categoria = st.selectbox("Categoria", ["Camisetas", "Calças", "Agasalhos", "Acessórios"])
                tamanho = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "Único"])
            with col2:
                cor = st.text_input("Cor", placeholder="Ex: Branco, Azul, Preto")
                preco = st.number_input("Preço (R$)", min_value=0.0, step=0.01, value=29.90)
            
            estoque = st.number_input("Estoque inicial", min_value=0, value=10)
            descricao = st.text_area("Descrição", placeholder="Detalhes do produto...")
            
            submitted = st.form_submit_button("✅ Cadastrar Produto", type="primary")
            
            if submitted:
                if nome:
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome do produto é obrigatório!")
    
    with tab2:
        st.header("📋 Produtos Cadastrados")
        produtos = listar_produtos()
        
        if produtos:
            dados = []
            for produto in produtos:
                dados.append({
                    'ID': produto[0],
                    'Nome': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Preço': f"R$ {produto[5]:.2f}",
                    'Estoque': produto[6],
                    'Descrição': produto[7] or 'N/A',
                    'Data Cadastro': produto[8]
                })
            
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Nenhum produto cadastrado")

elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos")
    st.info("🚀 Módulo em desenvolvimento...")
    
    # Aqui você pode implementar a gestão de pedidos
    st.write("Em breve: sistema completo de pedidos com múltiplos itens")

elif menu == "📈 Relatórios":
    st.title("📈 Relatórios e Analytics")
    st.info("📊 Módulo em desenvolvimento...")
    
    # Estatísticas básicas
    clientes = listar_clientes()
    produtos = listar_produtos()
    
    if clientes:
        st.subheader("Distribuição de Clientes por Escola")
        df_clientes = pd.DataFrame([{
            'Nome': c[1],
            'Escolas': c[4] or 'Sem escola'
        } for c in clientes])
        
        if not df_clientes.empty:
            contagem_escolas = df_clientes['Escolas'].value_counts()
            fig = px.pie(values=contagem_escolas.values, names=contagem_escolas.index, title="Clientes por Escola")
            st.plotly_chart(fig)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("""
**🌐 Sistema Online**
- **Banco:** PostgreSQL
- **Hospedagem:** Render.com
- **Status:** ✅ Operacional
""")

# Botão para recarregar dados
if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()
