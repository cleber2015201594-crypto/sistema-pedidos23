import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import sqlite3
import time
from contextlib import contextmanager

# =========================================
# 🚀 CONFIGURAÇÃO PARA RENDER
# =========================================

# Verificar se está rodando no Render
IS_RENDER = 'RENDER' in os.environ

# =========================================
# ⚡ OTIMIZAÇÕES DE PERFORMANCE - CORRIGIDAS
# =========================================

@st.cache_data(ttl=300)
def listar_escolas_cached():
    escolas = listar_escolas()
    # Converter sqlite3.Row para lista de dicionários serializáveis
    return [dict(escola) for escola in escolas]

@st.cache_data(ttl=300)
def listar_clientes_cached():
    clientes = listar_clientes()
    # Converter sqlite3.Row para lista de dicionários serializáveis
    return [dict(cliente) for cliente in clientes]

@st.cache_data(ttl=180)
def listar_produtos_por_escola_cached(escola_id):
    produtos = listar_produtos_por_escola(escola_id)
    # Converter sqlite3.Row para lista de dicionários serializáveis
    return [dict(produto) for produto in produtos]

@st.cache_data(ttl=120)
def listar_pedidos_por_escola_cached(escola_id=None):
    pedidos = listar_pedidos_por_escola(escola_id)
    # Converter sqlite3.Row para lista de dicionários serializáveis
    return [dict(pedido) for pedido in pedidos]

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO - SQLITE
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Estabelece conexão com SQLite"""
    try:
        conn = sqlite3.connect('fardamentos.db', check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        # Configurações de performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco SQLite com índices para performance"""
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
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(nome, tamanho, cor, escola_id)
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
            
            # 🔧 ÍNDICES PARA MELHOR PERFORMANCE
            cur.execute('CREATE INDEX IF NOT EXISTS idx_produtos_escola ON produtos(escola_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_escola ON pedidos(escola_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_pedido)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_pedido_itens_pedido ON pedido_itens(pedido_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_pedido_itens_produto ON pedido_itens(produto_id)')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                try:
                    cur.execute('''
                        INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                        VALUES (?, ?, ?, ?)
                    ''', (username, password_hash, nome, tipo))
                except Exception as e:
                    pass
            
            # Inserir escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                try:
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
                except Exception as e:
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
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = ? AND ativo = 1
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]  # sucesso, nome, tipo
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

def alterar_senha(username, senha_atual, nova_senha):
    """Altera a senha do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar senha atual
        cur.execute('SELECT password_hash FROM usuarios WHERE username = ?', (username,))
        resultado = cur.fetchone()
        
        if not resultado or not check_hashes(senha_atual, resultado[0]):
            return False, "Senha atual incorreta"
        
        # Atualizar senha
        nova_senha_hash = make_hashes(nova_senha)
        cur.execute(
            'UPDATE usuarios SET password_hash = ? WHERE username = ?',
            (nova_senha_hash, username)
        )
        conn.commit()
        return True, "Senha alterada com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_usuarios():
    """Lista todos os usuários (apenas para admin)"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, username, nome_completo, tipo, ativo, data_criacao 
            FROM usuarios 
            ORDER BY username
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []
    finally:
        conn.close()

def criar_usuario(username, password, nome_completo, tipo):
    """Cria novo usuário (apenas para admin)"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        password_hash = make_hashes(password)
        
        cur.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, tipo)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, nome_completo, tipo))
        
        conn.commit()
        return True, "Usuário criado com sucesso!"
        
    except sqlite3.IntegrityError:
        return False, "Username já existe"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
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

# Configuração da página (primeira coisa a ser executada)
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

# CONFIGURAÇÕES ESPECÍFICAS
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS - SQLITE
# =========================================

# FUNÇÃO PARA FORMATAR DATA NO PADRÃO BRASILEIRO
def formatar_data_brasil(data_str):
    """Converte data do formato YYYY-MM-DD para DD/MM/YYYY"""
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

# FUNÇÕES PARA ESCOLAS
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

def obter_escola_por_id(escola_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas WHERE id = ?", (escola_id,))
        resultado = cur.fetchone()
        return dict(resultado) if resultado else None
    except Exception as e:
        st.error(f"Erro ao obter escola: {e}")
        return None
    finally:
        conn.close()

# FUNÇÕES PARA CLIENTES
def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (?, ?, ?, ?)",
            (nome, telefone, email, data_cadastro)
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
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar se tem pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = ?", (cliente_id,))
        if cur.fetchone()[0] > 0:
            return False, "Cliente possui pedidos e não pode ser excluído"
        
        cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        return True, "Cliente excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÕES PARA PRODUTOS
def verificar_produto_duplicado(nome, tamanho, cor, escola_id):
    """Verifica se já existe um produto com as mesmas características"""
    conn = get_connection()
    if not conn:
        return True  # Se não conseguiu conectar, assume que existe para evitar duplicação
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT COUNT(*) FROM produtos 
            WHERE nome = ? AND tamanho = ? AND cor = ? AND escola_id = ?
        ''', (nome, tamanho, cor, escola_id))
        
        count = cur.fetchone()[0]
        return count > 0
        
    except Exception as e:
        st.error(f"Erro ao verificar produto duplicado: {e}")
        return True
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        # Verificar se produto já existe
        if verificar_produto_duplicado(nome, tamanho, cor, escola_id):
            return False, "❌ Já existe um produto com este nome, tamanho e cor para esta escola!"
        
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Erro: Produto duplicado para esta escola!"
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
                WHERE p.escola_id = ?
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
        st.error(f"Erro ao listar produtos: {e}")
        return []
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

def excluir_produto(produto_id):
    """Exclui um produto se não estiver em nenhum pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar se o produto está em algum pedido
        cur.execute("SELECT COUNT(*) FROM pedido_itens WHERE produto_id = ?", (produto_id,))
        count = cur.fetchone()[0]
        
        if count > 0:
            return False, "❌ Este produto está em pedidos e não pode ser excluído"
        
        # Excluir o produto
        cur.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        conn.commit()
        return True, "✅ Produto excluído com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÕES PARA PEDIDOS
def adicionar_pedido(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        # VERIFICAR ESTOQUE APENAS COMO ALERTA, NÃO BLOQUEAR
        alertas_estoque = []
        for item in itens:
            cur.execute("SELECT estoque, nome FROM produtos WHERE id = ?", (item['produto_id'],))
            produto = cur.fetchone()
            if produto and produto[0] < item['quantidade']:
                alertas_estoque.append(f"{produto[1]} - Estoque: {produto[0]}, Pedido: {item['quantidade']}")
        
        # Criar pedido mesmo com estoque insuficiente (apenas alerta)
        cur.execute('''
            INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, quantidade_total, valor_total, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.lastrowid
        
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, substotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            # ⚠️ REMOVIDA A ATUALIZAÇÃO DE ESTOQUE AQUI
        
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
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def baixar_estoque_pedido(pedido_id):
    """Baixa o estoque apenas quando o pedido é marcado como entregue"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Buscar itens do pedido
        cur.execute('''
            SELECT pi.produto_id, pi.quantidade, pr.nome, pr.estoque 
            FROM pedido_itens pi 
            JOIN produtos pr ON pi.produto_id = pr.id 
            WHERE pi.pedido_id = ?
        ''', (pedido_id,))
        itens = cur.fetchall()
        
        # Verificar estoque antes de baixar
        produtos_sem_estoque = []
        for item in itens:
            produto_id, quantidade, nome, estoque_atual = item
            if estoque_atual < quantidade:
                produtos_sem_estoque.append(f"{nome} (Estoque: {estoque_atual}, Necessário: {quantidade})")
        
        if produtos_sem_estoque:
            return False, f"Estoque insuficiente para: {', '.join(produtos_sem_estoque)}"
        
        # Baixar estoque
        for item in itens:
            produto_id, quantidade, nome, estoque_atual = item
            cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id))
        
        conn.commit()
        return True, "✅ Estoque baixado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao baixar estoque: {str(e)}"
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
            
            # Primeiro atualiza o status
            cur.execute('''
                UPDATE pedidos 
                SET status = ?, data_entrega_real = ? 
                WHERE id = ?
            ''', (novo_status, data_entrega, pedido_id))
            
            conn.commit()  # COMMIT ANTES DE BAIXAR ESTOQUE
            
            # Depois baixa o estoque em uma transação separada
            sucesso, msg = baixar_estoque_pedido(pedido_id)
            if not sucesso:
                # Se não conseguiu baixar estoque, reverte o status
                cur.execute('''
                    UPDATE pedidos 
                    SET status = 'Pronto para entrega', data_entrega_real = NULL 
                    WHERE id = ?
                ''', (pedido_id,))
                conn.commit()
                return False, f"Status não atualizado: {msg}"
            
            return True, "✅ Status do pedido atualizado e estoque baixado com sucesso!"
        else:
            cur.execute('''
                UPDATE pedidos 
                SET status = ? 
                WHERE id = ?
            ''', (novo_status, pedido_id))
            
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
        
        # Excluir pedido (estoque não é restaurado pois não foi baixado ainda)
        cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES PARA RELATÓRIOS - SQLITE
# =========================================

def gerar_relatorio_vendas_por_escola(escola_id=None):
    """Gera relatório de vendas por período e escola (exclui pedidos cancelados)"""
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
    """Gera relatório de produtos mais vendidos por escola (exclui pedidos cancelados)"""
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
# 🎨 INTERFACE PRINCIPAL - ATUALIZADA PARA DICIONÁRIOS
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Menu de gerenciamento de usuários (apenas para admin)
if st.session_state.tipo_usuario == 'admin':
    with st.sidebar.expander("👥 Gerenciar Usuários"):
        st.subheader("Novo Usuário")
        with st.form("novo_usuario"):
            novo_username = st.text_input("Username")
            nova_senha = st.text_input("Senha", type='password')
            nome_completo = st.text_input("Nome Completo")
            tipo = st.selectbox("Tipo", ["admin", "vendedor"])
            
            if st.form_submit_button("Criar Usuário"):
                if novo_username and nova_senha and nome_completo:
                    sucesso, msg = criar_usuario(novo_username, nova_senha, nome_completo, tipo)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
        
        st.subheader("Usuários do Sistema")
        usuarios = listar_usuarios()
        if usuarios:
            for usuario in usuarios:
                status = "✅ Ativo" if usuario[4] == 1 else "❌ Inativo"
                st.write(f"**{usuario[1]}** - {usuario[2]} ({usuario[3]}) - {status}")

# Menu de alteração de senha
with st.sidebar.expander("🔐 Alterar Senha"):
    with st.form("alterar_senha"):
        senha_atual = st.text_input("Senha Atual", type='password')
        nova_senha1 = st.text_input("Nova Senha", type='password')
        nova_senha2 = st.text_input("Confirmar Nova Senha", type='password')
        
        if st.form_submit_button("Alterar Senha"):
            if senha_atual and nova_senha1 and nova_senha2:
                if nova_senha1 == nova_senha2:
                    sucesso, msg = alterar_senha(st.session_state.username, senha_atual, nova_senha1)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("As novas senhas não coincidem")
            else:
                st.error("Preencha todos os campos")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.nome_usuario = None
    st.session_state.tipo_usuario = None
    st.rerun()

# Menu principal - ORGANIZADO POR ESCOLA
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Visão Geral")
elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos") 
elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
elif menu == "👕 Produtos":
    st.title("👕 Gestão de Produtos")
elif menu == "📦 Estoque":
    st.title("📦 Controle de Estoque")
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Detalhados")

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA - ATUALIZADAS PARA DICIONÁRIOS
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Métricas em Tempo Real")
    
    # Carregar dados usando cache
    escolas_dict = listar_escolas_cached()
    clientes_dict = listar_clientes_cached()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = 0
        for escola in escolas_dict:
            pedidos = listar_pedidos_por_escola_cached(escola['id'])
            total_pedidos += len(pedidos)
        st.metric("Total de Pedidos", total_pedidos)
    
    with col2:
        pedidos_pendentes = 0
        for escola in escolas_dict:
            pedidos = listar_pedidos_por_escola_cached(escola['id'])
            pedidos_pendentes += len([p for p in pedidos if p['status'] == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        st.metric("Clientes Ativos", len(clientes_dict))
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas_dict:
            produtos = listar_produtos_por_escola_cached(escola['id'])
            produtos_baixo_estoque += len([p for p in produtos if p['estoque'] < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Métricas por Escola
    st.header("🏫 Métricas por Escola")
    escolas_cols = st.columns(len(escolas_dict))
    
    for idx, escola in enumerate(escolas_dict):
        with escolas_cols[idx]:
            st.subheader(escola['nome'])
            
            # Pedidos da escola
            pedidos_escola = listar_pedidos_por_escola_cached(escola['id'])
            pedidos_pendentes_escola = len([p for p in pedidos_escola if p['status'] == 'Pendente'])
            
            # Produtos da escola
            produtos_escola = listar_produtos_por_escola_cached(escola['id'])
            produtos_baixo_estoque_escola = len([p for p in produtos_escola if p['estoque'] < 5])
            
            st.metric("Pedidos", len(pedidos_escola))
            st.metric("Pendentes", pedidos_pendentes_escola)
            st.metric("Produtos", len(produtos_escola))
            st.metric("Alerta Estoque", produtos_baixo_estoque_escola)
    
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
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        nome = st.text_input("👤 Nome completo*")
        telefone = st.text_input("📞 Telefone")
        email = st.text_input("📧 Email")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
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
        clientes_dict = listar_clientes_cached()
        
        if clientes_dict:
            dados = []
            for cliente in clientes_dict:
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
    
    with tab3:
        st.header("🗑️ Excluir Cliente")
        clientes_dict = listar_clientes_cached()
        
        if clientes_dict:
            cliente_selecionado = st.selectbox(
                "Selecione o cliente para excluir:",
                [f"{c['nome']} (ID: {c['id']})" for c in clientes_dict]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                st.warning("⚠️ Esta ação não pode ser desfeita!")
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, msg = excluir_cliente(cliente_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    escolas_dict = listar_escolas_cached()
    
    if not escolas_dict:
        st.error("❌ Nenhuma escola cadastrada. Cadastre escolas primeiro.")
        st.stop()
    
    # Seleção da escola PRIMEIRO
    escola_selecionada_nome = st.selectbox(
        "🏫 Selecione a Escola:",
        [e['nome'] for e in escolas_dict],
        key="produtos_escola"
    )
    escola_id = next(e['id'] for e in escolas_dict if e['nome'] == escola_selecionada_nome)
    
    st.header(f"👕 Produtos - {escola_selecionada_nome}")
    
    # Abas para diferentes funcionalidades
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista de Produtos", "➕ Cadastrar Novo", "📊 Estatísticas", "🗑️ Excluir Produto"])
    
    with tab1:
        # Lista organizada de produtos com busca/filtro
        produtos_dict = listar_produtos_por_escola_cached(escola_id)
        if produtos_dict:
            # Filtros rápidos
            col1, col2, col3 = st.columns(3)
            with col1:
                filtro_categoria = st.selectbox("Filtrar por categoria:", ["Todas"] + categorias_produtos)
            with col2:
                filtro_tamanho = st.selectbox("Filtrar por tamanho:", ["Todos"] + todos_tamanhos)
            with col3:
                busca_nome = st.text_input("Buscar por nome:")
            
            # Aplicar filtros
            produtos_filtrados = produtos_dict
            if filtro_categoria != "Todas":
                produtos_filtrados = [p for p in produtos_filtrados if p['categoria'] == filtro_categoria]
            if filtro_tamanho != "Todos":
                produtos_filtrados = [p for p in produtos_filtrados if p['tamanho'] == filtro_tamanho]
            if busca_nome:
                produtos_filtrados = [p for p in produtos_filtrados if busca_nome.lower() in p['nome'].lower()]
            
            # Exibir produtos
            for produto in produtos_filtrados:
                status_estoque = "✅" if produto['estoque'] >= 10 else "⚠️" if produto['estoque'] >= 5 else "❌"
                
                with st.expander(f"{status_estoque} {produto['nome']} - {produto['tamanho']} - {produto['cor']} | Estoque: {produto['estoque']} | R$ {produto['preco']:.2f}"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.write(f"**Categoria:** {produto['categoria']}")
                        st.write(f"**Descrição:** {produto['descricao'] or 'Sem descrição'}")
                        st.write(f"**Data Cadastro:** {formatar_data_brasil(produto['data_cadastro'])}")
                    with col2:
                        # Edição rápida de estoque
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
                                st.info("Quantidade não foi alterada")
        else:
            st.info("📭 Nenhum produto cadastrado para esta escola")
    
    with tab2:
        # Formulário simplificado de cadastro
        with st.form("novo_produto_form", clear_on_submit=True):
            st.subheader("➕ Cadastrar Novo Produto")
            
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("📝 Nome do Produto*", placeholder="Ex: Camiseta Polo")
                categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
            with col2:
                cor = st.text_input("🎨 Cor*", value="Branco", placeholder="Ex: Azul Marinho")
                preco = st.number_input("💰 Preço (R$)*", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 Estoque Inicial*", min_value=0, value=10)
            
            descricao = st.text_area("📄 Descrição (opcional)", placeholder="Detalhes do produto...")
            
            if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                if nome and cor:
                    # Verificar duplicação antes de tentar cadastrar
                    if verificar_produto_duplicado(nome, tamanho, cor, escola_id):
                        st.error("❌ Já existe um produto com este nome, tamanho e cor para esta escola!")
                    else:
                        sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                        if sucesso:
                            st.success(msg)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome e Cor")
    
    with tab3:
        # Estatísticas visuais
        produtos_dict = listar_produtos_por_escola_cached(escola_id)
        if produtos_dict:
            col1, col2, col3 = st.columns(3)
            with col1:
                total_produtos = len(produtos_dict)
                st.metric("Total de Produtos", total_produtos)
            with col2:
                total_estoque = sum(p['estoque'] for p in produtos_dict)
                st.metric("Estoque Total", total_estoque)
            with col3:
                baixo_estoque = len([p for p in produtos_dict if p['estoque'] < 5])
                st.metric("Produtos com Estoque Baixo", baixo_estoque)
            
            # Gráfico por categoria
            categorias_count = {}
            for p in produtos_dict:
                cat = p['categoria']
                categorias_count[cat] = categorias_count.get(cat, 0) + 1
            
            if categorias_count:
                df_categorias = pd.DataFrame({
                    'Categoria': list(categorias_count.keys()),
                    'Quantidade': list(categorias_count.values())
                })
                fig = px.pie(df_categorias, values='Quantidade', names='Categoria', title='Produtos por Categoria')
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("🗑️ Excluir Produto")
        produtos_dict = listar_produtos_por_escola_cached(escola_id)
        
        if produtos_dict:
            produto_selecionado = st.selectbox(
                "Selecione o produto para excluir:",
                [f"{p['nome']} - {p['tamanho']} - {p['cor']} (ID: {p['id']})" for p in produtos_dict]
            )
            
            if produto_selecionado:
                produto_id = int(produto_selecionado.split("(ID: ")[1].replace(")", ""))
                
                st.warning("⚠️ Esta ação não pode ser desfeita!")
                st.info("ℹ️ Só é possível excluir produtos que não estão em pedidos")
                
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, msg = excluir_produto(produto_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("📭 Nenhum produto cadastrado para esta escola")

elif menu == "📦 Estoque":
    escolas_dict = listar_escolas_cached()
    
    if not escolas_dict:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    # Abas por escola
    tabs = st.tabs([f"🏫 {e['nome']}" for e in escolas_dict])
    
    for idx, escola in enumerate(escolas_dict):
        with tabs[idx]:
            st.header(f"📦 Controle de Estoque - {escola['nome']}")
            
            produtos_dict = listar_produtos_por_escola_cached(escola['id'])
            
            if produtos_dict:
                # Métricas da escola
                col1, col2, col3, col4 = st.columns(4)
                total_produtos = len(produtos_dict)
                total_estoque = sum(p['estoque'] for p in produtos_dict)
                produtos_baixo_estoque = len([p for p in produtos_dict if p['estoque'] < 5])
                produtos_sem_estoque = len([p for p in produtos_dict if p['estoque'] == 0])
                
                with col1:
                    st.metric("Total Produtos", total_produtos)
                with col2:
                    st.metric("Estoque Total", total_estoque)
                with col3:
                    st.metric("Estoque Baixo", produtos_baixo_estoque)
                with col4:
                    st.metric("Sem Estoque", produtos_sem_estoque)
                
                # Tabela interativa de estoque
                st.subheader("📋 Ajuste de Estoque")
                
                for produto in produtos_dict:
                    status_estoque = "✅" if produto['estoque'] >= 10 else "⚠️" if produto['estoque'] >= 5 else "❌"
                    
                    with st.expander(f"{status_estoque} {produto['nome']} - {produto['tamanho']} - {produto['cor']} (Estoque: {produto['estoque']})"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**Categoria:** {produto['categoria']}")
                            st.write(f"**Preço:** R$ {produto['preco']:.2f}")
                            if produto['descricao']:
                                st.write(f"**Descrição:** {produto['descricao']}")
                        
                        with col2:
                            nova_quantidade = st.number_input(
                                "Nova quantidade",
                                min_value=0,
                                value=produto['estoque'],
                                key=f"estoque_{produto['id']}_{idx}"
                            )
                        
                        with col3:
                            if st.button("💾 Atualizar", key=f"btn_{produto['id']}_{idx}"):
                                if nova_quantidade != produto['estoque']:
                                    sucesso, msg = atualizar_estoque(produto['id'], nova_quantidade)
                                    if sucesso:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                                else:
                                    st.info("Quantidade não foi alterada")
                
                # Alertas de estoque baixo
                produtos_alerta = [p for p in produtos_dict if p['estoque'] < 5]
                if produtos_alerta:
                    st.subheader("🚨 Alertas de Estoque Baixo")
                    for produto in produtos_alerta:
                        status = "⚠️" if produto['estoque'] > 0 else "❌"
                        st.warning(f"{status} **{produto['nome']} - {produto['tamanho']} - {produto['cor']}**: Apenas {produto['estoque']} unidades em estoque")
            
            else:
                st.info(f"📭 Nenhum produto cadastrado para {escola['nome']}")

elif menu == "📦 Pedidos":
    escolas_dict = listar_escolas_cached()
    
    if not escolas_dict:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🆕 Novo Pedido", "📋 Pedidos em Andamento", "✅ Pedidos Entregues", "❌ Pedidos Cancelados"])
    
    with tab1:
        st.header("🆕 Criar Novo Pedido")
        
        # Passo 1: Selecionar Escola
        escola_nome = st.selectbox("🏫 Escola:", [e['nome'] for e in escolas_dict], key="nova_escola_pedido")
        escola_id = next(e['id'] for e in escolas_dict if e['nome'] == escola_nome)
        
        # Passo 2: Selecionar Cliente
        clientes_dict = listar_clientes_cached()
        if not clientes_dict:
            st.error("❌ Nenhum cliente cadastrado.")
        else:
            cliente_opcoes = [f"{c['nome']} (ID: {c['id']})" for c in clientes_dict]
            cliente_selecionado = st.selectbox("👤 Cliente:", cliente_opcoes)
            cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
            
            # Passo 3: Adicionar Itens
            st.subheader("🛒 Itens do Pedido")
            produtos_dict = listar_produtos_por_escola_cached(escola_id)
            
            if not produtos_dict:
                st.error(f"❌ Nenhum produto cadastrado para {escola_nome}")
            else:
                # Interface simplificada para adicionar itens
                if 'itens_pedido' not in st.session_state:
                    st.session_state.itens_pedido = []
                
                col1, col2, col3, col4 = st.columns([3,1,1,1])
                with col1:
                    produto_opcoes = [f"{p['nome']} | T: {p['tamanho']} | C: {p['cor']} | Est: {p['estoque']} | R$ {p['preco']:.2f}" for p in produtos_dict]
                    produto_sel = st.selectbox("Produto:", produto_opcoes)
                with col2:
                    qtd = st.number_input("Qtd:", min_value=1, value=1)
                with col3:
                    preco_unit = next(p['preco'] for p in produtos_dict if f"{p['nome']} | T: {p['tamanho']} | C: {p['cor']} | Est: {p['estoque']} | R$ {p['preco']:.2f}" == produto_sel)
                    st.write(f"R$ {preco_unit:.2f}")
                with col4:
                    if st.button("➕ Add", use_container_width=True):
                        produto_id = next(p['id'] for p in produtos_dict if f"{p['nome']} | T: {p['tamanho']} | C: {p['cor']} | Est: {p['estoque']} | R$ {p['preco']:.2f}" == produto_sel)
                        
                        item = {
                            'produto_id': produto_id,
                            'nome': next(p['nome'] for p in produtos_dict if p['id'] == produto_id),
                            'tamanho': next(p['tamanho'] for p in produtos_dict if p['id'] == produto_id),
                            'cor': next(p['cor'] for p in produtos_dict if p['id'] == produto_id),
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
        st.header("📋 Pedidos em Andamento")
        pedidos_dict = listar_pedidos_por_escola_cached()
        
        if pedidos_dict:
            # Filtrar apenas pedidos não entregues e não cancelados
            pedidos_em_andamento = [p for p in pedidos_dict if p['status'] not in ['Entregue', 'Cancelado']]
            
            if pedidos_em_andamento:
                for pedido in pedidos_em_andamento:
                    status_icon = {
                        'Pendente': '🟡',
                        'Em produção': '🟠', 
                        'Pronto para entrega': '🔵'
                    }.get(pedido['status'], '⚪')
                    
                    with st.expander(f"{status_icon} Pedido #{pedido['id']} - {pedido['cliente_nome']} - {pedido['escola_nome']} - R$ {float(pedido['valor_total']):.2f} - {pedido['status']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Cliente:** {pedido['cliente_nome']}")
                            st.write(f"**Escola:** {pedido['escola_nome']}")
                            st.write(f"**Data do Pedido:** {formatar_data_brasil(pedido['data_pedido'])}")
                            st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        
                        with col2:
                            st.write(f"**Forma de Pagamento:** {pedido['forma_pagamento']}")
                            st.write(f"**Quantidade Total:** {pedido['quantidade_total']}")
                            st.write(f"**Valor Total:** R$ {float(pedido['valor_total']):.2f}")
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
        st.header("✅ Pedidos Entregues")
        pedidos_dict = listar_pedidos_por_escola_cached()
        
        if pedidos_dict:
            # Filtrar apenas pedidos entregues
            pedidos_entregues = [p for p in pedidos_dict if p['status'] == 'Entregue']
            
            if pedidos_entregues:
                for pedido in pedidos_entregues:
                    with st.expander(f"✅ Pedido #{pedido['id']} - {pedido['cliente_nome']} - {pedido['escola_nome']} - R$ {float(pedido['valor_total']):.2f}"):
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
                            st.write(f"**Valor Total:** R$ {float(pedido['valor_total']):.2f}")
                            if pedido['observacoes']:
                                st.write(f"**Observações:** {pedido['observacoes']}")
            else:
                st.info("✅ Nenhum pedido entregue")
        else:
            st.info("📦 Nenhum pedido realizado")
    
    with tab4:
        st.header("❌ Pedidos Cancelados")
        pedidos_dict = listar_pedidos_por_escola_cached()
        
        if pedidos_dict:
            # Filtrar apenas pedidos cancelados
            pedidos_cancelados = [p for p in pedidos_dict if p['status'] == 'Cancelado']
            
            if pedidos_cancelados:
                for pedido in pedidos_cancelados:
                    with st.expander(f"❌ Pedido #{pedido['id']} - {pedido['cliente_nome']} - {pedido['escola_nome']} - R$ {float(pedido['valor_total']):.2f}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Cliente:** {pedido['cliente_nome']}")
                            st.write(f"**Escola:** {pedido['escola_nome']}")
                            st.write(f"**Data do Pedido:** {formatar_data_brasil(pedido['data_pedido'])}")
                            st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        
                        with col2:
                            st.write(f"**Forma de Pagamento:** {pedido['forma_pagamento']}")
                            st.write(f"**Quantidade Total:** {pedido['quantidade_total']}")
                            st.write(f"**Valor Total:** R$ {float(pedido['valor_total']):.2f}")
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
    escolas_dict = listar_escolas_cached()
    
    tab1, tab2, tab3 = st.tabs(["📊 Vendas por Escola", "📦 Produtos Mais Vendidos", "👥 Análise Completa"])
    
    with tab1:
        st.header("📊 Relatório de Vendas por Escola")
        
        escola_relatorio = st.selectbox(
            "Selecione a escola:",
            ["Todas as escolas"] + [e['nome'] for e in escolas_dict],
            key="relatorio_escola"
        )
        
        if escola_relatorio == "Todas as escolas":
            relatorio_vendas = gerar_relatorio_vendas_por_escola()
        else:
            escola_id = next(e['id'] for e in escolas_dict if e['nome'] == escola_relatorio)
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
        st.header("📦 Produtos Mais Vendidos")
        
        escola_produtos = st.selectbox(
            "Selecione a escola:",
            ["Todas as escolas"] + [e['nome'] for e in escolas_dict],
            key="produtos_relatorio"
        )
        
        if escola_produtos == "Todas as escolas":
            relatorio_produtos = gerar_relatorio_produtos_por_escola()
        else:
            escola_id = next(e['id'] for e in escolas_dict if e['nome'] == escola_produtos)
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
    
    with tab3:
        st.header("👥 Análise Completa do Sistema")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🏫 Escolas")
            escolas_count = len(escolas_dict)
            st.metric("Total de Escolas", escolas_count)
            
        with col2:
            st.subheader("👥 Clientes")
            clientes_dict = listar_clientes_cached()
            st.metric("Total de Clientes", len(clientes_dict))
            
        with col3:
            st.subheader("👕 Produtos")
            total_produtos = 0
            for escola in escolas_dict:
                produtos = listar_produtos_por_escola_cached(escola['id'])
                total_produtos += len(produtos)
            st.metric("Total de Produtos", total_produtos)
        
        # Resumo por escola
        st.subheader("📋 Resumo por Escola")
        resumo_data = []
        for escola in escolas_dict:
            produtos_escola = listar_produtos_por_escola_cached(escola['id'])
            pedidos_escola = listar_pedidos_por_escola_cached(escola['id'])
            # Filtrar apenas pedidos não cancelados para as vendas
            pedidos_nao_cancelados = [p for p in pedidos_escola if p['status'] != 'Cancelado']
            total_vendas = sum(float(p['valor_total']) for p in pedidos_nao_cancelados)
            
            resumo_data.append({
                'Escola': escola['nome'],
                'Produtos': len(produtos_escola),
                'Pedidos': len(pedidos_nao_cancelados),
                'Vendas (R$)': total_vendas
            })
        
        if resumo_data:
            st.dataframe(pd.DataFrame(resumo_data), use_container_width=True)
            
            # Gráfico de comparação entre escolas
            fig = px.bar(pd.DataFrame(resumo_data), x='Escola', y='Vendas (R$)',
                        title='Comparação de Vendas por Escola')
            st.plotly_chart(fig, use_container_width=True)

# =========================================
# 📊 MONITORAMENTO DE PERFORMANCE
# =========================================

def monitor_performance():
    """Função para monitorar performance do sistema"""
    if 'performance' not in st.session_state:
        st.session_state.performance = {
            'inicio': time.time(),
            'consultas': 0,
            'atualizacoes': 0
        }
    
    # Exibir métricas de performance no sidebar (apenas para admin)
    if st.session_state.get('logged_in') and st.session_state.get('tipo_usuario') == 'admin':
        with st.sidebar.expander("📊 Performance"):
            tempo_execucao = time.time() - st.session_state.performance['inicio']
            st.write(f"⏱️ Tempo sessão: {tempo_execucao:.1f}s")
            st.write(f"📈 Consultas: {st.session_state.performance['consultas']}")
            st.write(f"✏️ Atualizações: {st.session_state.performance['atualizacoes']}")
            
            # Botão para limpar cache
            if st.button("🔄 Limpar Cache"):
                st.cache_data.clear()
                st.success("Cache limpo!")
                st.rerun()

# Chamar monitoramento
monitor_performance()

# =========================================
# 🚀 HEALTH CHECK AUTOMÁTICO (RENDER)
# =========================================

if IS_RENDER:
    @st.cache_resource(ttl=600)
    def keep_alive():
        """Mantém o serviço ativo no Render"""
        try:
            import requests
            # Faz ping na própria aplicação a cada 10 minutos
            requests.get(f"https://{os.environ.get('RENDER_EXTERNAL_URL', '')}", timeout=10)
        except:
            pass
    
    # Executar health check
    keep_alive()

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v13.0\n\n🏫 **Organizado por Escola**\n🗄️ Banco SQLite\n⚡ **Performance Otimizada**\n🌐 **Pronto para Deploy**\n🔧 **Serialização Corrigida**")

# Botão para recarregar dados
if st.sidebar.button("🔄 Recarregar Dados"):
    st.cache_data.clear()
    st.rerun()
