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
    page_title="Sistema Fardamentos",
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
        return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados limpo"""
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
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                estoque INTEGER DEFAULT 0,
                descricao TEXT,
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
                escola_id INTEGER,
                status TEXT DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                data_entrega_real DATE,
                forma_pagamento TEXT,
                quantidade_total INTEGER,
                valor_total REAL,
                observacoes TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
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
        
        # Usuários padrão (SEM dados de treino A.I.)
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador Sistema', 'admin'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor Principal', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, nome, tipo))
        
        # Apenas escolas básicas (SEM produtos de exemplo)
        escolas_padrao = [
            ('Escola Municipal', 'Rua Principal, 123', '(11) 9999-8888', 'contato@escolamunicipal.com'),
        ]
        
        for nome, endereco, telefone, email in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone, email) VALUES (?, ?, ?, ?)', 
                         (nome, endereco, telefone, email))
        
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
# 🔧 FUNÇÕES DO BANCO DE DADOS (DO APP FUNCIONAL)
# =========================================

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
        return cur.fetchone()
    except Exception as e:
        st.error(f"Erro ao obter escola: {e}")
        return None
    finally:
        conn.close()

def adicionar_escola(nome, endereco, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute('''
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
            return False, "❌ Cliente possui pedidos e não pode ser excluído"
        
        cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        return True, "✅ Cliente excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def contar_clientes():
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM clientes')
        return cur.fetchone()[0]
    except:
        return 0
    finally:
        conn.close()

# FUNÇÕES PARA PRODUTOS
def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        
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
        cur.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id 
            WHERE p.ativo = 1
            ORDER BY p.categoria, p.nome
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
        return True, "✅ Estoque atualizado com sucesso!"
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
            
            # Atualizar estoque
            cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                       (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
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

def atualizar_status_pedido(pedido_id, novo_status):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        if novo_status == 'Entregue':
            data_entrega = datetime.now().strftime("%Y-%m-%d")
            cur.execute('''
                UPDATE pedidos 
                SET status = ?, data_entrega_real = ? 
                WHERE id = ?
            ''', (novo_status, data_entrega, pedido_id))
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
        
        # Restaurar estoque
        cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
        itens = cur.fetchall()
        
        for item in itens:
            produto_id, quantidade = item[0], item[1]
            cur.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id))
        
        # Excluir pedido
        cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "✅ Pedido excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 🤖 SISTEMA A.I. - PREVISÕES (SIMPLIFICADO)
# =========================================

def analise_estoque_inteligente():
    """Análise inteligente de estoque"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, p.estoque, e.nome as escola_nome
            FROM produtos p
            LEFT JOIN escolas e ON p.escola_id = e.id
            WHERE p.ativo = 1 AND p.estoque <= 5
            ORDER BY p.estoque ASC
        ''')
        
        alertas = []
        for produto in cursor.fetchall():
            nivel = "CRÍTICO" if produto['estoque'] == 0 else "ALERTA"
            alertas.append({
                "produto": produto['nome'],
                "escola": produto['escola_nome'],
                "estoque_atual": produto['estoque'],
                "nivel": nivel
            })
        
        return alertas
    except:
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
        writer.writerow(['Nome', 'Telefone', 'Email', 'Data Cadastro'])
        
        for row in cursor.fetchall():
            writer.writerow([
                row['nome'],
                row['telefone'] or '',
                row['email'] or '',
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
    """Gera CSV de produtos"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.nome, p.categoria, p.tamanho, p.cor, p.preco, p.estoque, 
                   e.nome as escola_nome
            FROM produtos p
            LEFT JOIN escolas e ON p.escola_id = e.id
            ORDER BY e.nome, p.nome
        ''')
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Produto', 'Categoria', 'Tamanho', 'Cor', 'Preço', 'Estoque', 'Escola'])
        
        for row in cursor.fetchall():
            writer.writerow([
                row['nome'],
                row['categoria'],
                row['tamanho'],
                row['cor'],
                f"R$ {row['preco']:.2f}",
                row['estoque'],
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
# 🏠 PÁGINA DE LOGIN (SIMPLIFICADA)
# =========================================

def pagina_login():
    """Página de login limpa"""
    st.title("👕 Sistema Fardamentos")
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

# =========================================
# 📱 DASHBOARD LIMPO
# =========================================

def mostrar_dashboard():
    """Dashboard principal limpo"""
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
        st.markdown("📦 **Produtos**")
        produtos = listar_produtos()
        st.markdown(f"<h2>{len(produtos)}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("🏫 **Escolas**")
        escolas = listar_escolas()
        st.markdown(f"<h2>{len(escolas)}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("📊 **Pedidos**")
        pedidos = listar_pedidos()
        st.markdown(f"<h2>{len(pedidos)}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Alertas importantes
    col1, col2 = st.columns(2)
    
    with col1:
        # Alertas de Estoque
        alertas_estoque = analise_estoque_inteligente()
        if alertas_estoque:
            st.markdown('<div class="danger-card">', unsafe_allow_html=True)
            st.markdown("### ⚠️ Alertas de Estoque")
            for alerta in alertas_estoque[:3]:
                st.write(f"**{alerta['produto']}** ({alerta['escola']})")
                st.write(f"Estoque: {alerta['estoque_atual']} - {alerta['nivel']}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("### ✅ Estoque em Dia")
            st.write("Todos os produtos com estoque adequado")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Ações rápidas
        st.markdown('<div class="ai-card">', unsafe_allow_html=True)
        st.markdown("### 🚀 Ações Rápidas")
        st.write("• Cadastrar novo cliente")
        st.write("• Registrar pedido")
        st.write("• Gerenciar produtos")
        st.write("• Ver relatórios")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 🚀 AÇÕES RÁPIDAS FUNCIONAIS
    st.markdown("---")
    st.subheader("🚀 Navegação Rápida")
    
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
        if st.button("📚 Produtos", use_container_width=True):
            st.session_state.menu = "📚 Produtos"
            st.rerun()
    
    with col4:
        if st.button("📊 Relatórios", use_container_width=True):
            st.session_state.menu = "📊 Relatórios"
            st.rerun()

# =========================================
# 👥 CLIENTES
# =========================================

def mostrar_clientes():
    """Interface de clientes"""
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
            email = st.text_input("Email", placeholder="cliente@email.com")
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente")
            if submitted:
                if not nome.strip():
                    st.error("❌ O nome é obrigatório!")
                else:
                    success, message = adicionar_cliente(
                        nome=nome.strip(),
                        telefone=telefone,
                        email=email
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

# =========================================
# 📦 PEDIDOS
# =========================================

def mostrar_pedidos():
    """Interface de pedidos"""
    st.header("📦 Gerenciar Pedidos")
    
    tab1, tab2 = st.tabs(["📋 Lista de Pedidos", "➕ Novo Pedido"])
    
    with tab1:
        st.subheader("Pedidos Realizados")
        
        pedidos = listar_pedidos()
        if not pedidos:
            st.info("Nenhum pedido encontrado.")
        else:
            for pedido in pedidos:
                status_color = {
                    'Pendente': '🟡',
                    'Produção': '🔵', 
                    'Pronto': '🟢',
                    'Entregue': '✅'
                }
                
                with st.expander(f"{status_color.get(pedido['status'], '📦')} Pedido #{pedido['id']} - {pedido['cliente_nome']}"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Cliente:** {pedido['cliente_nome']}")
                        st.write(f"**Escola:** {pedido['escola_nome']}")
                        st.write(f"**Data:** {pedido['data_pedido']}")
                    
                    with col2:
                        st.write(f"**Status:** {pedido['status']}")
                        st.write(f"**Entrega Prevista:** {pedido['data_entrega_prevista']}")
                        st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                    
                    with col3:
                        # Atualizar status
                        novo_status = st.selectbox(
                            "Status",
                            ["Pendente", "Produção", "Pronto", "Entregue"],
                            index=["Pendente", "Produção", "Pronto", "Entregue"].index(pedido['status']),
                            key=f"status_{pedido['id']}"
                        )
                        
                        if st.button("Atualizar", key=f"upd_{pedido['id']}"):
                            success, message = atualizar_status_pedido(pedido['id'], novo_status)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        
                        if st.button("Excluir", key=f"del_ped_{pedido['id']}"):
                            success, message = excluir_pedido(pedido['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
    
    with tab2:
        st.subheader("Criar Novo Pedido")
        
        clientes = listar_clientes()
        escolas = listar_escolas()
        
        if not clientes:
            st.warning("Nenhum cliente cadastrado. Cadastre clientes primeiro!")
            return
        
        if not escolas:
            st.warning("Nenhuma escola cadastrada. Cadastre escolas primeiro!")
            return
        
        with st.form("novo_pedido_form"):
            # Selecionar cliente
            cliente_opcoes = {f"{c['nome']} - {c['telefone'] or 'N/A'}": c['id'] for c in clientes}
            cliente_selecionado = st.selectbox("Selecione o cliente:", options=list(cliente_opcoes.keys()))
            cliente_id = cliente_opcoes[cliente_selecionado]
            
            # Selecionar escola
            escola_opcoes = {e['nome']: e['id'] for e in escolas}
            escola_selecionada = st.selectbox("Selecione a escola:", options=list(escola_opcoes.keys()))
            escola_id = escola_opcoes[escola_selecionada]
            
            # Data de entrega
            data_entrega = st.date_input("Data de Entrega Prevista", min_value=date.today())
            
            # Forma de pagamento
            forma_pagamento = st.selectbox(
                "Forma de Pagamento:",
                ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"]
            )
            
            observacoes = st.text_area("Observações:")
            
            # Sistema de produtos
            st.subheader("🛒 Produtos do Pedido")
            produtos = listar_produtos()
            produtos_filtrados = [p for p in produtos if p['escola_id'] == escola_id]
            
            if not produtos_filtrados:
                st.warning(f"Nenhum produto cadastrado para {escola_selecionada}")
                return
            
            # Carrinho de compras
            if 'carrinho' not in st.session_state:
                st.session_state.carrinho = []
            
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                produto_opcoes = {f"{p['id']} - {p['nome']} ({p['tamanho']}) - R$ {p['preco']:.2f}": p for p in produtos_filtrados}
                produto_selecionado = st.selectbox("Selecione o produto:", options=list(produto_opcoes.keys()))
            
            with col2:
                quantidade = st.number_input("Quantidade:", min_value=1, value=1)
            
            with col3:
                st.write("")
                st.write("")
                if st.button("➕ Adicionar"):
                    if produto_selecionado:
                        produto_info = produto_opcoes[produto_selecionado]
                        
                        if quantidade > produto_info['estoque']:
                            st.error(f"❌ Estoque insuficiente! Disponível: {produto_info['estoque']}")
                        else:
                            item = {
                                'produto_id': produto_info['id'],
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
            if st.form_submit_button("✅ Finalizar Pedido", type="primary"):
                if not st.session_state.carrinho:
                    st.error("Adicione itens ao pedido!")
                else:
                    success, pedido_id = adicionar_pedido(
                        cliente_id=cliente_id,
                        escola_id=escola_id,
                        itens=st.session_state.carrinho,
                        data_entrega=data_entrega.strftime("%Y-%m-%d"),
                        forma_pagamento=forma_pagamento,
                        observacoes=observacoes
                    )
                    
                    if success:
                        st.success(f"✅ Pedido #{pedido_id} criado com sucesso!")
                        st.session_state.carrinho = []
                        st.rerun()
                    else:
                        st.error(f"❌ Erro ao criar pedido: {pedido_id}")

# =========================================
# 📚 PRODUTOS
# =========================================

def mostrar_produtos():
    """Interface de produtos"""
    st.header("📚 Gerenciar Produtos")
    
    tab1, tab2 = st.tabs(["📋 Lista de Produtos", "➕ Novo Produto"])
    
    with tab1:
        st.subheader("📋 Produtos Cadastrados")
        
        produtos = listar_produtos()
        if not produtos:
            st.info("Nenhum produto cadastrado.")
        else:
            for produto in produtos:
                with st.expander(f"📦 {produto['nome']} - {produto['escola_nome']}"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Categoria:** {produto['categoria']}")
                        st.write(f"**Tamanho:** {produto['tamanho']}")
                        st.write(f"**Cor:** {produto['cor']}")
                    
                    with col2:
                        st.write(f"**Preço:** R$ {produto['preco']:.2f}")
                        st.write(f"**Estoque:** {produto['estoque']}")
                        if produto['descricao']:
                            st.write(f"**Descrição:** {produto['descricao']}")
                    
                    with col3:
                        # Atualizar estoque
                        novo_estoque = st.number_input(
                            "Estoque", 
                            min_value=0, 
                            value=produto['estoque'],
                            key=f"estoque_{produto['id']}"
                        )
                        
                        if st.button("Atualizar", key=f"upd_est_{produto['id']}"):
                            success, message = atualizar_estoque(produto['id'], novo_estoque)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Produto")
        
        escolas = listar_escolas()
        if not escolas:
            st.error("Cadastre escolas primeiro!")
        else:
            with st.form("novo_produto_form", clear_on_submit=True):
                nome = st.text_input("Nome do Produto*")
                
                col1, col2 = st.columns(2)
                with col1:
                    categoria = st.selectbox("Categoria", ["Camiseta", "Calça", "Agasalho", "Short", "Acessório", "Uniforme"])
                    tamanho = st.text_input("Tamanho*", placeholder="P, M, G, 38, 42, etc")
                    cor = st.text_input("Cor*")
                with col2:
                    preco = st.number_input("Preço de Venda*", min_value=0.0, format="%.2f")
                    estoque = st.number_input("Estoque Inicial", min_value=0, value=0)
                
                descricao = st.text_area("Descrição (opcional)")
                
                escola_selecionada = st.selectbox(
                    "Escola*",
                    options=[e['nome'] for e in escolas]
                )
                
                if st.form_submit_button("✅ Cadastrar Produto"):
                    if nome and tamanho and cor and preco > 0:
                        escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada)
                        success, message = adicionar_produto(
                            nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Preencha todos os campos obrigatórios!")

# =========================================
# 📊 RELATÓRIOS
# =========================================

def mostrar_relatorios():
    """Interface de relatórios"""
    st.header("📊 Relatórios e Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Exportar Dados")
        
        if st.button("📋 Exportar Clientes para CSV"):
            csv_data = gerar_csv_clientes()
            if csv_data:
                baixar_csv(csv_data, "clientes")
            else:
                st.error("Erro ao gerar CSV de clientes")
        
        if st.button("📚 Exportar Produtos para CSV"):
            csv_data = gerar_csv_produtos()
            if csv_data:
                baixar_csv(csv_data, "produtos")
            else:
                st.error("Erro ao gerar CSV de produtos")
    
    with col2:
        st.subheader("Métricas do Sistema")
        
        st.metric("Total de Clientes", contar_clientes())
        st.metric("Produtos Cadastrados", len(listar_produtos()))
        st.metric("Escolas Parceiras", len(listar_escolas()))
        st.metric("Pedidos Realizados", len(listar_pedidos()))
        
        # Alertas de estoque
        alertas = analise_estoque_inteligente()
        if alertas:
            st.warning(f"⚠️ {len(alertas)} produtos com estoque baixo")

# =========================================
# ⚙️ ADMINISTRAÇÃO
# =========================================

def mostrar_administracao():
    """Interface administrativa"""
    st.header("⚙️ Administração do Sistema")
    
    tab1, tab2 = st.tabs(["🏫 Gerenciar Escolas", "🔧 Sistema"])
    
    with tab1:
        st.subheader("🏫 Gerenciar Escolas")
        
        # Listar escolas
        escolas = listar_escolas()
        if escolas:
            st.write("**Escolas Cadastradas:**")
            for escola in escolas:
                st.write(f"**{escola['nome']}**")
                st.write(f"Telefone: {escola['telefone']} | Email: {escola['email']}")
                st.write(f"Endereço: {escola['endereco']}")
                st.markdown("---")
        else:
            st.info("Nenhuma escola cadastrada.")
        
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
        st.subheader("🔧 Configurações do Sistema")
        
        if st.button("🔄 Reinicializar Banco de Dados"):
            with st.spinner("Reinicializando..."):
                if init_db():
                    st.success("✅ Banco reinicializado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao reinicializar banco!")
        
        st.info("""
        **Sugestões para Melhorar o Sistema:**
        
        1. **Backup Automático** - Implementar backup diário do banco
        2. **Notificações** - Alertas por email para estoque baixo
        3. **App Mobile** - Versão mobile para vendedores externos
        4. **Integração Pagamento** - Conexão com gateways de pagamento
        5. **Relatórios Avançados** - Gráficos e analytics detalhados
        6. **Controle de Acesso** - Permissões por perfil de usuário
        7. **API REST** - Integração com outros sistemas
        """)

# =========================================
# 🧩 MENU PRINCIPAL
# =========================================

def mostrar_menu_principal():
    """Menu de navegação principal"""
    st.sidebar.title("👕 Menu Principal")
    st.sidebar.markdown(f"**Usuário:** {st.session_state.nome_completo}")
    st.sidebar.markdown("---")
    
    menu_options = ["🏠 Dashboard", "👥 Clientes", "📦 Pedidos", "📚 Produtos", "📊 Relatórios", "⚙️ Administração"]
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
    elif menu == "📚 Produtos":
        mostrar_produtos()
    elif menu == "📊 Relatórios":
        mostrar_relatorios()
    elif menu == "⚙️ Administração":
        mostrar_administracao()

if __name__ == "__main__":
    main()
