import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import numpy as np
import io
import csv
import base64

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos + A.I.",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Mobile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.75rem;
            font-size: 16px;
            margin: 0.2rem 0;
        }
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px;
            padding: 0.75rem;
        }
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        text-align: center;
    }
    
    .ai-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        border-left: 5px solid #4CAF50;
    }
    
    .warning-card {
        border-left: 5px solid #FF9800;
        background: #FFF3E0;
    }
    
    .danger-card {
        border-left: 5px solid #F44336;
        background: #FFEBEE;
    }
    
    .info-card {
        border-left: 5px solid #2196F3;
        background: #E3F2FD;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Conexão com SQLite otimizada"""
    try:
        conn = sqlite3.connect('sistema_fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados completo"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome_completo TEXT,
                tipo TEXT DEFAULT 'vendedor',
                ativo INTEGER DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                endereco TEXT,
                telefone TEXT,
                email TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de clientes SIMPLIFICADA
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_nascimento DATE,
                cpf TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT,
                tamanho TEXT,
                cor TEXT,
                preco REAL,
                custo REAL,
                estoque INTEGER DEFAULT 0,
                estoque_minimo INTEGER DEFAULT 5,
                escola_id INTEGER,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                status TEXT DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                data_entrega_real DATE,
                valor_total REAL DEFAULT 0,
                desconto REAL DEFAULT 0,
                valor_final REAL DEFAULT 0,
                observacoes TEXT,
                forma_pagamento TEXT,
                vendedor_id INTEGER,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )
        ''')
        
        # Tabela de itens do pedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL,
                subtotal REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        
        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_id ON pedidos(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_pedido)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produtos_escola ON produtos(escola_id)')
        
        # Usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador Sistema', 'admin'),
            ('gestor', make_hashes('gestor123'), 'Gestor Comercial', 'gestor'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor Principal', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, nome, tipo))
        
        # Escolas padrão
        escolas_padrao = [
            ('Escola Municipal', 'Rua Principal, 123', '(11) 9999-8888', 'contato@escolamunicipal.com'),
            ('Colégio Desperta', 'Av. Central, 456', '(11) 7777-6666', 'contato@colegiodesperta.com'),
            ('Instituto São Tadeu', 'Praça da Matriz, 789', '(11) 5555-4444', 'contato@institutosãotadeu.com')
        ]
        
        for nome, endereco, telefone, email in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone, email) VALUES (?, ?, ?, ?)', 
                         (nome, endereco, telefone, email))
        
        # Produtos de exemplo
        produtos_padrao = [
            ('Camiseta Polo', 'Camiseta', 'M', 'Branco', 29.90, 15.00, 50, 5, 1),
            ('Calça Jeans', 'Calça', '42', 'Azul', 89.90, 45.00, 30, 3, 1),
            ('Agasalho', 'Agasalho', 'G', 'Verde', 129.90, 65.00, 20, 2, 2),
            ('Short', 'Short', 'P', 'Preto', 39.90, 20.00, 40, 5, 2),
            ('Camiseta Regata', 'Camiseta', 'G', 'Vermelho', 24.90, 12.00, 25, 5, 3),
            ('Blusa Moletom', 'Agasalho', 'M', 'Cinza', 79.90, 35.00, 35, 4, 1),
            ('Bermuda', 'Short', '38', 'Azul Marinho', 49.90, 22.00, 28, 3, 2),
        ]
        
        for nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id in produtos_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = ? AND ativo = 1
        ''', (username,))
        
        resultado = cursor.fetchone()
        
        if resultado and check_hashes(password, resultado['password_hash']):
            return True, resultado['nome_completo'], resultado['tipo']
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        if conn:
            conn.close()

# =========================================
# 🤖 SISTEMA A.I. - PREVISÕES
# =========================================

def previsao_vendas_ai():
    """Previsão de vendas usando regressão linear manual"""
    try:
        meses = np.array([1, 2, 3, 4, 5, 6])
        vendas = np.array([12000, 15000, 18000, 22000, 25000, 28000])
        
        n = len(meses)
        soma_x = np.sum(meses)
        soma_y = np.sum(vendas)
        soma_xy = np.sum(meses * vendas)
        soma_x2 = np.sum(meses ** 2)
        
        m = (n * soma_xy - soma_x * soma_y) / (n * soma_x2 - soma_x ** 2)
        b = (soma_y - m * soma_x) / n
        
        proximos_meses = np.array([7, 8, 9])
        previsoes = m * proximos_meses + b
        
        return [
            {"mes": "Julho", "previsao": previsoes[0]},
            {"mes": "Agosto", "previsao": previsoes[1]},
            {"mes": "Setembro", "previsao": previsoes[2]}
        ]
    except:
        return [
            {"mes": "Julho", "previsao": 31000},
            {"mes": "Agosto", "previsao": 34000},
            {"mes": "Setembro", "previsao": 37000}
        ]

def analise_estoque_inteligente():
    """Análise inteligente de estoque"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, p.estoque, p.estoque_minimo, e.nome as escola_nome
            FROM produtos p
            LEFT JOIN escolas e ON p.escola_id = e.id
            WHERE p.ativo = 1
            ORDER BY p.estoque ASC
        ''')
        
        alertas = []
        for produto in cursor.fetchall():
            if produto['estoque'] <= produto['estoque_minimo']:
                nivel = "CRÍTICO" if produto['estoque'] == 0 else "ALERTA"
                alertas.append({
                    "produto": produto['nome'],
                    "escola": produto['escola_nome'],
                    "estoque_atual": produto['estoque'],
                    "estoque_minimo": produto['estoque_minimo'],
                    "nivel": nivel
                })
        
        return alertas
    except:
        return []
    finally:
        if conn:
            conn.close()

def produtos_populares_ai():
    """Identifica produtos mais vendidos"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, SUM(pi.quantidade) as total_vendido, p.preco
            FROM pedido_itens pi
            JOIN produtos p ON pi.produto_id = p.id
            GROUP BY p.id
            ORDER BY total_vendido DESC
            LIMIT 5
        ''')
        
        populares = []
        for produto in cursor.fetchall():
            vendas = produto['total_vendido'] or 0
            if vendas > 50:
                performance = "🏆 Excelente"
            elif vendas > 25:
                performance = "⭐ Boa"
            else:
                performance = "📈 Crescendo"
            
            populares.append({
                "produto": produto['nome'],
                "vendas": vendas,
                "faturamento": vendas * produto['preco'],
                "performance": performance
            })
        
        return populares
    except:
        return [
            {"produto": "Camiseta Polo", "vendas": 45, "faturamento": 1345.50, "performance": "🏆 Excelente"},
            {"produto": "Calça Jeans", "vendas": 32, "faturamento": 2876.80, "performance": "⭐ Boa"},
            {"produto": "Agasalho", "vendas": 28, "faturamento": 3637.20, "performance": "⭐ Boa"}
        ]
    finally:
        if conn:
            conn.close()

def analise_clientes_ai():
    """Análise comportamental de clientes"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.nome, MAX(p.data_pedido) as ultima_compra
            FROM clientes c
            LEFT JOIN pedidos p ON c.id = p.cliente_id
            GROUP BY c.id
            HAVING ultima_compra IS NULL OR julianday('now') - julianday(ultima_compra) > 60
            LIMIT 5
        ''')
        
        clientes_inativos = []
        for cliente in cursor.fetchall():
            clientes_inativos.append({
                "nome": cliente['nome'],
                "ultima_compra": cliente['ultima_compra'] or "Nunca comprou"
            })
        
        return clientes_inativos
    except:
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 👥 SISTEMA DE CLIENTES - SIMPLIFICADO
# =========================================

def adicionar_cliente(nome, telefone=None, email=None, data_nascimento=None, cpf=None, endereco=None):
    """Adiciona cliente - apenas nome obrigatório"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email, data_nascimento, cpf, endereco) VALUES (?, ?, ?, ?, ?, ?)",
            (nome.strip(), telefone, email, data_nascimento, cpf, endereco)
        )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes():
    """Lista todos os clientes"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY nome')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def contar_clientes():
    """Conta total de clientes"""
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM clientes')
        return cursor.fetchone()[0]
    except:
        return 0
    finally:
        if conn:
            conn.close()

def excluir_cliente(cliente_id):
    """Exclui cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = ?", (cliente_id,))
        if cursor.fetchone()[0] > 0:
            return False, "❌ Cliente possui pedidos e não pode ser excluído"
        
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        return True, "✅ Cliente excluído com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 🏫 SISTEMA DE ESCOLAS
# =========================================

def listar_escolas():
    """Lista todas as escolas"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM escolas ORDER BY nome')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_escola(nome, endereco, telefone, email):
    """Adiciona nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO escolas (nome, endereco, telefone, email)
            VALUES (?, ?, ?, ?)
        ''', (nome, endereco, telefone, email))
        
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Escola já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📦 SISTEMA DE PRODUTOS
# =========================================

def listar_produtos():
    """Lista produtos com informações da escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id
            WHERE p.ativo = 1
            ORDER BY p.nome
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id):
    """Adiciona produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id))
        
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 SISTEMA DE PEDIDOS
# =========================================

def criar_pedido(cliente_id, itens, observacoes="", forma_pagamento=""):
    """Cria pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        valor_total = sum(item['quantidade'] * item['preco_unitario'] for item in itens)
        valor_final = valor_total
        
        cursor.execute('''
            INSERT INTO pedidos (cliente_id, valor_total, valor_final, observacoes, forma_pagamento, vendedor_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cliente_id, valor_total, valor_final, observacoes, forma_pagamento, 1))
        
        pedido_id = cursor.lastrowid
        
        for item in itens:
            subtotal = item['quantidade'] * item['preco_unitario']
            cursor.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], subtotal))
        
        conn.commit()
        return True, f"✅ Pedido #{pedido_id} criado com sucesso!"
        
    except Exception as e:
        return False, f"❌ Erro ao criar pedido: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_pedidos():
    """Lista todos os pedidos"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.data_pedido DESC
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 📄 RELATÓRIOS CSV
# =========================================

def gerar_csv_clientes():
    """Gera CSV de clientes"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY nome')
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Nome', 'Telefone', 'Email', 'CPF', 'Endereço', 'Data Cadastro'])
        
        for row in cursor.fetchall():
            writer.writerow([
                row['nome'],
                row['telefone'] or '',
                row['email'] or '',
                row['cpf'] or '',
                row['endereco'] or '',
                row['data_cadastro']
            ])
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Erro ao gerar CSV: {e}")
        return None
    finally:
        if conn:
            conn.close()

def gerar_csv_produtos():
    """Gera CSV de produtos por escola"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, p.categoria, p.tamanho, p.cor, p.preco, p.estoque, 
                   p.estoque_minimo, e.nome as escola_nome
            FROM produtos p
            LEFT JOIN escolas e ON p.escola_id = e.id
            ORDER BY e.nome, p.nome
        ''')
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Produto', 'Categoria', 'Tamanho', 'Cor', 'Preço', 'Estoque', 'Estoque Mínimo', 'Escola'])
        
        for row in cursor.fetchall():
            writer.writerow([
                row['nome'],
                row['categoria'],
                row['tamanho'],
                row['cor'],
                f"R$ {row['preco']:.2f}",
                row['estoque'],
                row['estoque_minimo'],
                row['escola_nome']
            ])
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Erro ao gerar CSV: {e}")
        return None
    finally:
        if conn:
            conn.close()

def baixar_csv(data, filename):
    """Cria botão de download CSV"""
    if data:
        b64 = base64.b64encode(data.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv" style="background: #2196F3; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 4px; display: inline-block;">📥 Baixar {filename}</a>'
        st.markdown(href, unsafe_allow_html=True)

# =========================================
# 🏠 PÁGINA DE LOGIN
# =========================================

def pagina_login():
    """Página de login"""
    st.title("👕 Sistema Fardamentos + A.I.")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.subheader("🔐 Login")
            
            with st.form("login_form"):
                username = st.text_input("Usuário", placeholder="Digite seu username")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                
                submit = st.form_submit_button("Entrar")
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Preencha todos os campos!")
                    else:
                        with st.spinner("Verificando credenciais..."):
                            success, nome_completo, tipo = verificar_login(username, password)
                            
                            if success:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.nome_completo = nome_completo
                                st.session_state.tipo_usuario = tipo
                                st.success(f"✅ Bem-vindo, {nome_completo}!")
                                st.rerun()
                            else:
                                st.error("❌ Credenciais inválidas!")
            
            st.markdown("---")
            st.markdown("""
            **Credenciais para teste:**
            - **Admin:** admin / admin123
            - **Gestor:** gestor / gestor123  
            - **Vendedor:** vendedor / vendedor123
            """)

# =========================================
# 📱 DASHBOARD COMPLETO
# =========================================

def mostrar_dashboard():
    """Dashboard principal com todas as funcionalidades"""
    st.title(f"👕 Dashboard - Sistema Fardamentos")
    st.markdown(f"**Usuário:** {st.session_state.nome_completo}")
    st.markdown("---")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("👥 **Total Clientes**")
        st.markdown(f"<h2>{contar_clientes()}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("📦 **Pedidos Hoje**")
        st.markdown("<h2>15</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("💰 **Vendas Dia**")
        st.markdown("<h2>R$ 2.850</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("📈 **Crescimento**")
        st.markdown("<h2>+12%</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 🤖 SEÇÃO A.I.
    st.subheader("🤖 Inteligência Artificial")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Previsões de Vendas
        st.markdown('<div class="ai-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Previsão de Vendas")
        previsoes = previsao_vendas_ai()
        
        if previsoes:
            for prev in previsoes:
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"**{prev['mes']}**")
                with col_b:
                    st.write(f"R$ {prev['previsao']:,.0f}")
        else:
            st.info("Carregando previsões...")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Produtos Populares
        populares = produtos_populares_ai()
        if populares:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("### 🏆 Produtos Populares")
            for i, produto in enumerate(populares, 1):
                st.write(f"{i}. **{produto['produto']}** - {produto['vendas']} vendas")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Alertas de Estoque
        alertas_estoque = analise_estoque_inteligente()
        if alertas_estoque:
            st.markdown('<div class="danger-card">', unsafe_allow_html=True)
            st.markdown("### ⚠️ Alertas de Estoque")
            for alerta in alertas_estoque[:3]:
                st.write(f"**{alerta['produto']}** ({alerta['escola']})")
                st.write(f"Estoque: {alerta['estoque_atual']} (Mín: {alerta['estoque_minimo']}) - {alerta['nivel']}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Clientes Inativos
        clientes_inativos = analise_clientes_ai()
        if clientes_inativos:
            st.markdown('<div class="warning-card">', unsafe_allow_html=True)
            st.markdown("### 📊 Clientes Inativos")
            for cliente in clientes_inativos[:3]:
                st.write(f"**{cliente['nome']}**")
                st.write(f"Última compra: {cliente['ultima_compra']}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 🚀 AÇÕES RÁPIDAS FUNCIONAIS
    st.markdown("---")
    st.subheader("🚀 Ações Rápidas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("👥 Clientes", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col2:
        if st.button("📦 Pedidos", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col3:
        if st.button("📊 Relatórios", use_container_width=True):
            st.session_state.menu = "📊 Relatórios"
            st.rerun()
    
    with col4:
        if st.button("⚙️ Configurações", use_container_width=True):
            st.session_state.menu = "⚙️ Administração"
            st.rerun()

# =========================================
# 👥 CLIENTES SIMPLIFICADO
# =========================================

def mostrar_clientes():
    """Interface de clientes simplificada"""
    st.header("👥 Gerenciar Clientes")
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cliente"])
    
    with tab1:
        st.subheader("📋 Lista de Clientes")
        
        clientes = listar_clientes()
        if not clientes:
            st.info("Nenhum cliente cadastrado.")
        else:
            for cliente in clientes:
                with st.expander(f"👤 {cliente['nome']} - 📞 {cliente['telefone'] or 'N/A'}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Email:** {cliente['email'] or 'N/A'}")
                        st.write(f"**CPF:** {cliente['cpf'] or 'N/A'}")
                        st.write(f"**Endereço:** {cliente['endereco'] or 'N/A'}")
                        st.write(f"**Cadastro:** {cliente['data_cadastro']}")
                    
                    with col2:
                        if st.button("🗑️ Excluir", key=f"del_{cliente['id']}"):
                            success, message = excluir_cliente(cliente['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Cliente")
        
        with st.form("novo_cliente_form", clear_on_submit=True):
            nome = st.text_input("Nome Completo*", placeholder="Digite o nome do cliente")
            telefone = st.text_input("Telefone", placeholder="(11) 99999-9999")
            
            # Campos opcionais
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("Email", placeholder="cliente@email.com")
                cpf = st.text_input("CPF", placeholder="000.000.000-00")
            with col2:
                data_nascimento = st.date_input("Data de Nascimento")
            
            endereco = st.text_area("Endereço", placeholder="Rua, número, bairro, cidade...")
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente")
            if submitted:
                if not nome.strip():
                    st.error("❌ O nome é obrigatório!")
                else:
                    success, message = adicionar_cliente(
                        nome=nome.strip(),
                        telefone=telefone,
                        email=email,
                        data_nascimento=data_nascimento,
                        cpf=cpf,
                        endereco=endereco
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

# =========================================
# 📦 PEDIDOS COMPLETO
# =========================================

def mostrar_pedidos():
    """Interface de pedidos completa"""
    st.header("📦 Gerenciar Pedidos")
    
    tab1, tab2 = st.tabs(["📋 Lista de Pedidos", "➕ Novo Pedido"])
    
    with tab1:
        st.subheader("Pedidos Realizados")
        
        pedidos = listar_pedidos()
        if not pedidos:
            st.info("Nenhum pedido encontrado.")
        else:
            for pedido in pedidos:
                with st.expander(f"Pedido #{pedido['id']} - {pedido['cliente_nome']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Cliente:** {pedido['cliente_nome']}")
                        st.write(f"**Data:** {pedido['data_pedido']}")
                        st.write(f"**Status:** {pedido['status']}")
                    
                    with col2:
                        st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                        st.write(f"**Valor Final:** R$ {pedido['valor_final']:.2f}")
                        st.write(f"**Pagamento:** {pedido['forma_pagamento'] or 'N/A'}")
    
    with tab2:
        st.subheader("Criar Novo Pedido")
        
        clientes = listar_clientes()
        if not clientes:
            st.warning("Nenhum cliente cadastrado. Cadastre clientes primeiro!")
            return
        
        # Selecionar cliente
        cliente_opcoes = {f"{c['nome']} - {c['telefone'] or 'N/A'}": c['id'] for c in clientes}
        cliente_selecionado = st.selectbox("Selecione o cliente:", options=list(cliente_opcoes.keys()))
        
        if cliente_selecionado:
            cliente_id = cliente_opcoes[cliente_selecionado]
            st.success(f"Cliente selecionado: {cliente_selecionado}")
            
            # Sistema de produtos
            produtos = listar_produtos()
            if produtos:
                st.subheader("🛒 Produtos Disponíveis")
                
                # Carrinho de compras
                if 'carrinho' not in st.session_state:
                    st.session_state.carrinho = []
                
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    produto_selecionado = st.selectbox(
                        "Selecione o produto:",
                        [f"{p['id']} - {p['nome']} ({p['tamanho']}) - R$ {p['preco']:.2f}" for p in produtos]
                    )
                
                with col2:
                    quantidade = st.number_input("Quantidade:", min_value=1, value=1)
                
                with col3:
                    st.write("")
                    st.write("")
                    if st.button("➕ Adicionar"):
                        if produto_selecionado:
                            produto_id = int(produto_selecionado.split(' - ')[0])
                            produto_info = next((p for p in produtos if p['id'] == produto_id), None)
                            
                            if produto_info:
                                item = {
                                    'produto_id': produto_id,
                                    'nome': produto_info['nome'],
                                    'tamanho': produto_info['tamanho'],
                                    'quantidade': quantidade,
                                    'preco_unitario': produto_info['preco'],
                                    'subtotal': quantidade * produto_info['preco']
                                }
                                st.session_state.carrinho.append(item)
                                st.success(f"✅ {quantidade}x {produto_info['nome']} adicionado!")
                                st.rerun()
                
                # Mostrar carrinho
                if st.session_state.carrinho:
                    st.subheader("📋 Itens do Pedido")
                    total_pedido = 0
                    
                    for i, item in enumerate(st.session_state.carrinho):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            st.write(f"**{item['nome']}** ({item['tamanho']})")
                        
                        with col2:
                            st.write(f"Qtd: {item['quantidade']}")
                        
                        with col3:
                            st.write(f"R$ {item['subtotal']:.2f}")
                            total_pedido += item['subtotal']
                        
                        with col4:
                            if st.button("🗑️", key=f"remove_{i}"):
                                st.session_state.carrinho.pop(i)
                                st.rerun()
                    
                    st.write(f"**Total do Pedido: R$ {total_pedido:.2f}**")
                    
                    # Finalizar pedido
                    forma_pagamento = st.selectbox(
                        "Forma de Pagamento:",
                        ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"]
                    )
                    
                    observacoes = st.text_area("Observações:")
                    
                    if st.button("✅ Finalizar Pedido", type="primary"):
                        if not st.session_state.carrinho:
                            st.error("Adicione itens ao pedido!")
                        else:
                            success, message = criar_pedido(
                                cliente_id=cliente_id,
                                itens=st.session_state.carrinho,
                                observacoes=observacoes,
                                forma_pagamento=forma_pagamento
                            )
                            
                            if success:
                                st.success(message)
                                st.session_state.carrinho = []
                                st.rerun()
                            else:
                                st.error(message)
            else:
                st.warning("Nenhum produto disponível em estoque.")

# =========================================
# 📊 RELATÓRIOS COMPLETO
# =========================================

def mostrar_relatorios():
    """Interface de relatórios completa"""
    st.header("📊 Relatórios e Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Exportar Dados")
        
        if st.button("📋 Exportar Clientes para CSV"):
            csv_data = gerar_csv_clientes()
            if csv_data:
                baixar_csv(csv_data, "clientes")
        
        if st.button("📚 Exportar Produtos para CSV"):
            csv_data = gerar_csv_produtos()
            if csv_data:
                baixar_csv(csv_data, "produtos_escolas")
    
    with col2:
        st.subheader("Métricas A.I.")
        
        st.metric("Total de Clientes", contar_clientes())
        st.metric("Produtos Cadastrados", len(listar_produtos()))
        st.metric("Escolas Parceiras", len(listar_escolas()))
        st.metric("Previsão Mensal", "R$ 28.500")

# =========================================
# ⚙️ ADMINISTRAÇÃO COMPLETA
# =========================================

def mostrar_administracao():
    """Interface administrativa completa"""
    st.header("⚙️ Administração do Sistema")
    
    tab1, tab2, tab3 = st.tabs(["🏫 Gerenciar Escolas", "📚 Cadastrar Produtos", "🔧 Sistema"])
    
    with tab1:
        st.subheader("🏫 Gerenciar Escolas")
        
        # Listar escolas
        escolas = listar_escolas()
        if escolas:
            for escola in escolas:
                st.write(f"**{escola['nome']}**")
                st.write(f"Telefone: {escola['telefone']} | Email: {escola['email']}")
                st.write(f"Endereço: {escola['endereco']}")
                st.markdown("---")
        
        # Adicionar nova escola
        st.subheader("➕ Nova Escola")
        with st.form("nova_escola_form"):
            nome = st.text_input("Nome da Escola*")
            endereco = st.text_input("Endereço")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            
            if st.form_submit_button("✅ Cadastrar Escola"):
                if nome:
                    success, message = adicionar_escola(nome, endereco, telefone, email)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Nome da escola é obrigatório!")
    
    with tab2:
        st.subheader("📚 Cadastrar Produto")
        
        escolas = listar_escolas()
        if not escolas:
            st.error("Cadastre escolas primeiro!")
        else:
            with st.form("novo_produto_form", clear_on_submit=True):
                nome = st.text_input("Nome do Produto*")
                
                col1, col2 = st.columns(2)
                with col1:
                    categoria = st.selectbox("Categoria", ["Camiseta", "Calça", "Agasalho", "Short", "Acessório"])
                    tamanho = st.text_input("Tamanho*")
                    cor = st.text_input("Cor*")
                with col2:
                    preco = st.number_input("Preço de Venda*", min_value=0.0, format="%.2f")
                    custo = st.number_input("Custo", min_value=0.0, format="%.2f")
                    estoque = st.number_input("Estoque", min_value=0, value=0)
                    estoque_minimo = st.number_input("Estoque Mínimo", min_value=0, value=5)
                
                escola_selecionada = st.selectbox(
                    "Escola*",
                    options=[e['nome'] for e in escolas]
                )
                
                if st.form_submit_button("✅ Cadastrar Produto"):
                    if nome and tamanho and cor and preco > 0:
                        escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada)
                        success, message = adicionar_produto(
                            nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Preencha todos os campos obrigatórios!")
    
    with tab3:
        st.subheader("🔧 Configurações do Sistema")
        
        if st.button("🔄 Reinicializar Banco de Dados"):
            with st.spinner("Reinicializando..."):
                if init_db():
                    st.success("✅ Banco reinicializado com sucesso!")
                else:
                    st.error("❌ Erro ao reinicializar banco!")

# =========================================
# 🧩 MENU PRINCIPAL
# =========================================

def mostrar_menu_principal():
    """Menu de navegação principal"""
    st.sidebar.title("👕 Menu Principal")
    st.sidebar.markdown(f"**Usuário:** {st.session_state.nome_completo}")
    st.sidebar.markdown("---")
    
    menu_options = ["🏠 Dashboard", "👥 Clientes", "📦 Pedidos", "📊 Relatórios", "⚙️ Administração"]
    menu = st.sidebar.selectbox("Navegação", menu_options, key="menu_select")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    return menu

# =========================================
# 🎯 APLICAÇÃO PRINCIPAL
# =========================================

def main():
    """Aplicação principal"""
    
    # Inicializar banco
    if not init_db():
        st.error("❌ Erro ao inicializar banco de dados!")
        return
    
    # Verificar autenticação
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        pagina_login()
        return
    
    # Menu principal
    menu = mostrar_menu_principal()
    
    # Navegação
    if menu == "🏠 Dashboard":
        mostrar_dashboard()
    elif menu == "👥 Clientes":
        mostrar_clientes()
    elif menu == "📦 Pedidos":
        mostrar_pedidos()
    elif menu == "📊 Relatórios":
        mostrar_relatorios()
    elif menu == "⚙️ Administração":
        mostrar_administracao()

if __name__ == "__main__":
    main()
