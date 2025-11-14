import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import sqlite3
import requests
from io import StringIO

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Usuários e senhas 
usuarios = {
    "admin": make_hashes("Admin@2024!"),
    "vendedor": make_hashes("Vendas@123")
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
    return False

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🗄️ SISTEMA DE BANCO DE DADOS SQLite
# =========================================

def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect('fardamentos.db')
    c = conn.cursor()
    
    # Tabela de clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT NOT NULL,
                  telefone TEXT,
                  email TEXT,
                  data_cadastro TEXT)''')
    
    # Tabela de escolas (agora separada)
    c.execute('''CREATE TABLE IF NOT EXISTS escolas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT NOT NULL)''')
    
    # Tabela de relação cliente-escola (muitos para muitos)
    c.execute('''CREATE TABLE IF NOT EXISTS cliente_escolas
                 (cliente_id INTEGER,
                  escola_id INTEGER,
                  FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                  FOREIGN KEY(escola_id) REFERENCES escolas(id),
                  PRIMARY KEY(cliente_id, escola_id))''')
    
    # Tabela de produtos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT NOT NULL,
                  categoria TEXT,
                  tamanho TEXT,
                  cor TEXT,
                  preco REAL,
                  estoque INTEGER,
                  descricao TEXT,
                  data_cadastro TEXT)''')
    
    # Tabela de pedidos
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cliente_id INTEGER,
                  escola_id INTEGER,
                  status TEXT,
                  data_pedido TEXT,
                  data_entrega_prevista TEXT,
                  quantidade_total INTEGER,
                  valor_total REAL,
                  observacoes TEXT,
                  FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                  FOREIGN KEY(escola_id) REFERENCES escolas(id))''')
    
    # Tabela de itens do pedido
    c.execute('''CREATE TABLE IF NOT EXISTS pedido_itens
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pedido_id INTEGER,
                  produto_id INTEGER,
                  quantidade INTEGER,
                  preco_unitario REAL,
                  subtotal REAL,
                  FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
                  FOREIGN KEY(produto_id) REFERENCES produtos(id))''')
    
    # Inserir escolas padrão se não existirem
    escolas_padrao = ["Municipal", "Desperta", "São Tadeu"]
    for escola in escolas_padrao:
        c.execute("INSERT OR IGNORE INTO escolas (nome) VALUES (?)", (escola,))
    
    conn.commit()
    conn.close()

def carregar_dados_github():
    """Carrega dados de um arquivo CSV do GitHub"""
    try:
        # URL do arquivo CSV no GitHub (substitua pela sua URL)
        url = "https://raw.githubusercontent.com/seu-usuario/seu-repositorio/main/dados.csv"
        response = requests.get(url)
        
        if response.status_code == 200:
            # Ler CSV
            df = pd.read_csv(StringIO(response.text))
            st.success("✅ Dados carregados do GitHub com sucesso!")
            return df
        else:
            st.warning("⚠️ Não foi possível carregar dados do GitHub")
            return None
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None

# Inicializar banco de dados
init_db()

# =========================================
# 🚀 SISTEMA PRINCIPAL
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.write(f"👤 Usuário: **{st.session_state.username}**")

# CONFIGURAÇÕES ESPECÍFICAS - TAMANHOS CORRETOS
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

# PRODUTOS REAIS
tipos_camisetas = [
    "Camiseta Básica", 
    "Camiseta Regata", 
    "Camiseta Manga Longa"
]

tipos_calcas = [
    "Calça Jeans",
    "Calça Tactel", 
    "Calça Moletom",
    "Bermuda",
    "Short",
    "Short Saia"
]

tipos_agasalhos = [
    "Blusão",
    "Moletom"
]

# =========================================
# 🗄️ FUNÇÕES DO BANCO DE DADOS
# =========================================

def get_connection():
    return sqlite3.connect('fardamentos.db')

# Funções para Clientes
def adicionar_cliente(nome, telefone, email, escolas_ids):
    conn = get_connection()
    c = conn.cursor()
    
    # Inserir cliente
    data_cadastro = datetime.now().strftime("%d/%m/%Y")
    c.execute("INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (?, ?, ?, ?)",
              (nome, telefone, email, data_cadastro))
    
    cliente_id = c.lastrowid
    
    # Inserir relações com escolas
    for escola_id in escolas_ids:
        c.execute("INSERT INTO cliente_escolas (cliente_id, escola_id) VALUES (?, ?)",
                  (cliente_id, escola_id))
    
    conn.commit()
    conn.close()

def listar_clientes():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''SELECT c.*, GROUP_CONCAT(e.nome, ', ') as escolas
                 FROM clientes c
                 LEFT JOIN cliente_escolas ce ON c.id = ce.cliente_id
                 LEFT JOIN escolas e ON ce.escola_id = e.id
                 GROUP BY c.id''')
    
    clientes = c.fetchall()
    conn.close()
    
    return clientes

def excluir_cliente(cliente_id):
    conn = get_connection()
    c = conn.cursor()
    
    # Verificar se existem pedidos para este cliente
    c.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = ?", (cliente_id,))
    count_pedidos = c.fetchone()[0]
    
    if count_pedidos > 0:
        conn.close()
        return False, "Não é possível excluir cliente com pedidos associados"
    
    # Excluir relações com escolas
    c.execute("DELETE FROM cliente_escolas WHERE cliente_id = ?", (cliente_id,))
    
    # Excluir cliente
    c.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    
    conn.commit()
    conn.close()
    return True, "Cliente excluído com sucesso"

# Funções para Pedidos
def adicionar_pedido(cliente_id, escola_id, itens, data_entrega, observacoes):
    conn = get_connection()
    c = conn.cursor()
    
    # Calcular totais
    quantidade_total = sum(item['quantidade'] for item in itens)
    valor_total = sum(item['subtotal'] for item in itens)
    
    # Inserir pedido
    data_pedido = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('''INSERT INTO pedidos 
                 (cliente_id, escola_id, status, data_pedido, data_entrega_prevista, 
                  quantidade_total, valor_total, observacoes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (cliente_id, escola_id, 'Pendente', data_pedido, data_entrega, 
               quantidade_total, valor_total, observacoes))
    
    pedido_id = c.lastrowid
    
    # Inserir itens do pedido
    for item in itens:
        c.execute('''INSERT INTO pedido_itens 
                     (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                     VALUES (?, ?, ?, ?, ?)''',
                  (pedido_id, item['produto_id'], item['quantidade'], 
                   item['preco_unitario'], item['subtotal']))
        
        # Atualizar estoque
        c.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                  (item['quantidade'], item['produto_id']))
    
    conn.commit()
    conn.close()
    return pedido_id

def listar_pedidos():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                 FROM pedidos p
                 JOIN clientes c ON p.cliente_id = c.id
                 JOIN escolas e ON p.escola_id = e.id
                 ORDER BY p.id DESC''')
    
    pedidos = c.fetchall()
    conn.close()
    return pedidos

def excluir_pedido(pedido_id):
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Restaurar estoque dos itens do pedido
        c.execute('''SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?''', 
                  (pedido_id,))
        itens = c.fetchall()
        
        for produto_id, quantidade in itens:
            c.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
                      (quantidade, produto_id))
        
        # Excluir itens do pedido
        c.execute("DELETE FROM pedido_itens WHERE pedido_id = ?", (pedido_id,))
        
        # Excluir pedido
        c.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        conn.close()
        return True, "Pedido excluído com sucesso"
    except Exception as e:
        conn.close()
        return False, f"Erro ao excluir pedido: {str(e)}"

# Funções para Produtos
def listar_produtos():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM produtos")
    produtos = c.fetchall()
    conn.close()
    return produtos

def listar_escolas():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM escolas")
    escolas = c.fetchall()
    conn.close()
    return escolas

# =========================================
# 🎨 NAVEGAÇÃO
# =========================================

st.sidebar.title("👕 Sistema de Fardamentos")

menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Fardamentos", "📦 Estoque", "📈 Relatórios"]
if 'menu' not in st.session_state:
    st.session_state.menu = menu_options[0]

menu = st.sidebar.radio("Navegação", menu_options, index=menu_options.index(st.session_state.menu))
st.session_state.menu = menu

# HEADER DINÂMICO
if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Visão Geral")
elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos") 
elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
elif menu == "👕 Fardamentos":
    st.title("👕 Gestão de Fardamentos")
elif menu == "📦 Estoque":
    st.title("📦 Controle de Estoque")
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Detalhados")

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Métricas em Tempo Real")
    
    # Carregar dados
    pedidos = listar_pedidos()
    clientes = listar_clientes()
    produtos = listar_produtos()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Pedidos", len(pedidos))
    
    with col2:
        pedidos_pendentes = len([p for p in pedidos if p[3] == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        st.metric("Clientes Ativos", len(clientes))
    
    with col4:
        produtos_baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Ações Rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 Cadastrar Fardamento", use_container_width=True):
            st.session_state.menu = "👕 Fardamentos"
            st.rerun()
    
    with col4:
        if st.button("📥 Importar Dados", use_container_width=True):
            df = carregar_dados_github()
            if df is not None:
                st.dataframe(df)

elif menu == "📦 Pedidos":
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Novo Pedido", "📋 Listar Pedidos", "🔄 Alterar Status", "✏️ Editar Pedido", "🗑️ Excluir Pedido"])
    
    with tab1:
        st.header("📝 Novo Pedido de Fardamento")
        
        # Seleção de cliente
        clientes = listar_clientes()
        if clientes:
            cliente_opcoes = [f"{c[1]} (Escolas: {c[5]})" for c in clientes]
            cliente_selecionado = st.selectbox("👤 Cliente", cliente_opcoes)
            
            # Seleção de escola para este pedido
            escolas = listar_escolas()
            escola_selecionada = st.selectbox("🏫 Escola para este pedido", 
                                            [e[1] for e in escolas])
        else:
            st.warning("👥 Cadastre clientes primeiro!")
            cliente_selecionado = None
        
        # Sistema de múltiplos itens (similar ao anterior, mas adaptado para SQL)
        # ... (código similar ao anterior, adaptado para usar funções SQL)
        
    with tab5:
        st.header("🗑️ Excluir Pedido")
        pedidos = listar_pedidos()
        
        if pedidos:
            pedido_opcoes = [f"ID: {p[0]} - {p[8]} - {p[9]} - R$ {p[7]:.2f}" for p in pedidos]
            pedido_excluir = st.selectbox("Selecione o pedido para excluir", pedido_opcoes)
            
            if pedido_excluir:
                pedido_id = int(pedido_excluir.split(' - ')[0].replace('ID: ', ''))
                
                st.warning("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
                st.info("📋 **Itens do pedido serão restaurados no estoque**")
                
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, mensagem = excluir_pedido(pedido_id)
                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)
        else:
            st.info("📋 Nenhum pedido cadastrado")

elif menu == "👥 Clientes":
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "✏️ Editar Cliente", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        nome_cliente = st.text_input("👤 Nome do Cliente*")
        telefone = st.text_input("📞 Telefone (WhatsApp)")
        email = st.text_input("📧 Email (opcional)")
        
        # Seleção múltipla de escolas
        st.subheader("🏫 Escolas do Cliente")
        escolas = listar_escolas()
        escolas_selecionadas = st.multiselect("Selecione as escolas do cliente",
                                            [e[1] for e in escolas],
                                            help="O cliente pode ter acesso a múltiplas escolas")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome_cliente and escolas_selecionadas:
                # Converter nomes das escolas para IDs
                escolas_ids = [e[0] for e in escolas if e[1] in escolas_selecionadas]
                adicionar_cliente(nome_cliente, telefone, email, escolas_ids)
                st.success("✅ Cliente cadastrado com sucesso!")
                st.balloons()
            else:
                st.error("❌ Nome do cliente e pelo menos uma escola são obrigatórios!")
    
    with tab4:
        st.header("🗑️ Excluir Cliente")
        clientes = listar_clientes()
        
        if clientes:
            cliente_opcoes = [f"{c[1]} (ID: {c[0]}) - Escolas: {c[5]}" for c in clientes]
            cliente_excluir = st.selectbox("Selecione o cliente para excluir", cliente_opcoes)
            
            if cliente_excluir:
                cliente_id = int(cliente_excluir.split('ID: ')[1].split(')')[0])
                
                st.warning("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
                st.info("ℹ️ **Apenas clientes sem pedidos podem ser excluídos**")
                
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, mensagem = excluir_cliente(cliente_id)
                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)
        else:
            st.info("👥 Nenhum cliente cadastrado")

# ... (as outras páginas similares adaptadas para SQL)

# =========================================
# 🚀 DEPLOY ONLINE - SUGESTÕES
# =========================================

st.sidebar.markdown("---")
st.sidebar.header("🌐 Deploy Online")

with st.sidebar.expander("Onde Hospedar Gratuitamente"):
    st.write("""
    **🚀 Plataformas Gratuitas:**
    
    **1. Streamlit Community Cloud**
    - ✅ Mais fácil para Streamlit
    - ✅ Conecta direto com GitHub
    - ✅ Gratuito para apps públicos
    
    **2. Heroku**
    - ✅ Suporte Python
    - ⚠️ Precisa de config extra
    - ⚠️ Limite de horas gratuitas
    
    **3. PythonAnywhere**
    - ✅ Fácil para Python
    - ✅ Banco SQLite incluso
    - ⚠️ Interface menos moderna
    
    **4. Railway/Render**
    - ✅ Alternativas modernas
    - ✅ Docker support
    - ⚠️ Configuração mais complexa
    """)

st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v7.0 - COM BANCO DE DADOS")

# Botão para carregar dados do GitHub
if st.sidebar.button("📥 Carregar Dados do GitHub"):
    df = carregar_dados_github()
    if df is not None:
        st.sidebar.success("Dados carregados!")
