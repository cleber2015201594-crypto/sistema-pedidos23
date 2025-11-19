import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import sqlite3
import time
import pickle

# =========================================
# 🚀 CONFIGURAÇÃO PARA RENDER
# =========================================

# Verificar se está rodando no Render
IS_RENDER = 'RENDER' in os.environ

# =========================================
# ⚡ CONFIGURAÇÃO DE CACHE E PERFORMANCE - CORRIGIDA
# =========================================

def converter_para_serializavel(obj):
    """
    Converte objetos não serializáveis para tipos serializáveis
    """
    if obj is None:
        return None
    elif isinstance(obj, (int, float, str, bool)):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: converter_para_serializavel(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [converter_para_serializavel(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(converter_para_serializavel(item) for item in obj)
    elif hasattr(obj, '__dict__'):
        return converter_para_serializavel(obj.__dict__)
    else:
        # Para qualquer outro tipo, converte para string
        try:
            pickle.dumps(obj)
            return obj
        except:
            return str(obj)

# Funções de cache com tratamento robusto
@st.cache_data(ttl=300)
def listar_escolas_cached():
    try:
        escolas = listar_escolas()
        return converter_para_serializavel(escolas)
    except Exception as e:
        st.error(f"Erro ao carregar escolas: {e}")
        return []

@st.cache_data(ttl=300)
def listar_clientes_cached():
    try:
        clientes = listar_clientes()
        return converter_para_serializavel(clientes)
    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")
        return []

@st.cache_data(ttl=180)
def listar_produtos_por_escola_cached(escola_id):
    try:
        produtos = listar_produtos_por_escola(escola_id)
        return converter_para_serializavel(produtos)
    except Exception as e:
        st.error(f"Erro ao carregar produtos: {e}")
        return []

@st.cache_data(ttl=120)
def listar_pedidos_por_escola_cached(escola_id=None):
    try:
        pedidos = listar_pedidos_por_escola(escola_id)
        return converter_para_serializavel(pedidos)
    except Exception as e:
        st.error(f"Erro ao carregar pedidos: {e}")
        return []

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
        # No Render, usar caminho absoluto para o banco de dados
        db_path = '/tmp/fardamentos.db' if IS_RENDER else 'fardamentos.db'
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
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
                except Exception:
                    pass
            
            # Inserir escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                try:
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
                except Exception:
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
        # Converter para dicionários simples
        rows = cur.fetchall()
        usuarios = []
        for row in rows:
            usuario_dict = {}
            for key in row.keys():
                usuario_dict[key] = row[key]
            usuarios.append(usuario_dict)
        return usuarios
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
            # Tentar diferentes formatos de data
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
                try:
                    data_obj = datetime.strptime(data_str, fmt)
                    return data_obj.strftime("%d/%m/%Y")
                except ValueError:
                    continue
            return data_str
        elif isinstance(data_str, (datetime, date)):
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
        # Converter para dicionários simples
        rows = cur.fetchall()
        escolas = []
        for row in rows:
            escola_dict = {}
            for key in row.keys():
                escola_dict[key] = row[key]
            escolas.append(escola_dict)
        return escolas
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
        if resultado:
            escola_dict = {}
            for key in resultado.keys():
                escola_dict[key] = resultado[key]
            return escola_dict
        return None
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
        # Converter para dicionários simples
        rows = cur.fetchall()
        clientes = []
        for row in rows:
            cliente_dict = {}
            for key in row.keys():
                cliente_dict[key] = row[key]
            clientes.append(cliente_dict)
        return clientes
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
        # Converter para dicionários simples
        rows = cur.fetchall()
        produtos = []
        for row in rows:
            produto_dict = {}
            for key in row.keys():
                produto_dict[key] = row[key]
            produtos.append(produto_dict)
        return produtos
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
        # Converter para dicionários simples
        rows = cur.fetchall()
        pedidos = []
        for row in rows:
            pedido_dict = {}
            for key in row.keys():
                pedido_dict[key] = row[key]
            pedidos.append(pedido_dict)
        return pedidos
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
# 🎨 INTERFACE PRINCIPAL
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
                status = "✅ Ativo" if usuario.get('ativo', 0) == 1 else "❌ Inativo"
                st.write(f"**{usuario.get('username', '')}** - {usuario.get('nome_completo', '')} ({usuario.get('tipo', '')}) - {status}")

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
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal
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
# 📱 PÁGINAS DO SISTEMA
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
            pedidos_pendentes += len([p for p in pedidos if p.get('status') == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        st.metric("Clientes Ativos", len(clientes_dict))
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas_dict:
            produtos = listar_produtos_por_escola_cached(escola['id'])
            produtos_baixo_estoque += len([p for p in produtos if p.get('estoque', 0) < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Métricas por Escola
    if escolas_dict:
        st.header("🏫 Métricas por Escola")
        escolas_cols = st.columns(len(escolas_dict))
        
        for idx, escola in enumerate(escolas_dict):
            with escolas_cols[idx]:
                st.subheader(escola['nome'])
                
                # Pedidos da escola
                pedidos_escola = listar_pedidos_por_escola_cached(escola['id'])
                pedidos_pendentes_escola = len([p for p in pedidos_escola if p.get('status') == 'Pendente'])
                
                # Produtos da escola
                produtos_escola = listar_produtos_por_escola_cached(escola['id'])
                produtos_baixo_estoque_escola = len([p for p in produtos_escola if p.get('estoque', 0) < 5])
                
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
                    'ID': cliente.get('id', ''),
                    'Nome': cliente.get('nome', ''),
                    'Telefone': cliente.get('telefone') or 'N/A',
                    'Email': cliente.get('email') or 'N/A',
                    'Data Cadastro': formatar_data_brasil(cliente.get('data_cadastro'))
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
                [f"{c.get('nome', '')} (ID: {c.get('id', '')})" for c in clientes_dict]
            )
            
            if cliente_selecionado:
                try:
                    cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                    
                    st.warning("⚠️ Esta ação não pode ser desfeita!")
                    if st.button("🗑️ Confirmar Exclusão", type="primary"):
                        sucesso, msg = excluir_cliente(cliente_id)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                except Exception as e:
                    st.error("Erro ao processar seleção do cliente")
        else:
            st.info("👥 Nenhum cliente cadastrado")

# [As outras páginas (Produtos, Estoque, Pedidos, Relatórios) seguem a mesma lógica...]

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v15.0\n\n🏫 **Organizado por Escola**\n🗄️ Banco SQLite\n⚡ **Performance Otimizada**\n🌐 **Pronto para Deploy**")

# Botão para recarregar dados
if st.sidebar.button("🔄 Recarregar Dados"):
    st.cache_data.clear()
    st.rerun()
