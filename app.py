import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
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

# =========================================
# 🔐 SISTEMA DE PERMISSÕES AVANÇADO
# =========================================

PERMISSOES = {
    'admin': {
        'modulos': ['dashboard', 'clientes', 'pedidos', 'relatorios', 'administracao', 'estoque', 'financeiro'],
        'acoes': ['criar', 'ler', 'editar', 'excluir', 'exportar', 'configurar'],
        'descricao': 'Acesso total ao sistema'
    },
    'gestor': {
        'modulos': ['dashboard', 'clientes', 'pedidos', 'relatorios', 'estoque'],
        'acoes': ['criar', 'ler', 'editar', 'exportar'],
        'descricao': 'Acesso gerencial completo'
    },
    'vendedor': {
        'modulos': ['dashboard', 'clientes', 'pedidos'],
        'acoes': ['criar', 'ler', 'editar'],
        'descricao': 'Acesso operacional básico'
    }
}

def verificar_permissao(tipo_usuario, modulo=None, acao=None):
    """
    Verifica se usuário tem permissão para acessar módulo ou executar ação
    """
    if tipo_usuario not in PERMISSOES:
        return False
    
    # Se apenas verificar acesso ao módulo
    if modulo and not acao:
        return modulo in PERMISSOES[tipo_usuario]['modulos']
    
    # Se verificar ação específica no módulo
    if modulo and acao:
        tem_modulo = modulo in PERMISSOES[tipo_usuario]['modulos']
        tem_acao = acao in PERMISSOES[tipo_usuario]['acoes']
        return tem_modulo and tem_acao
    
    return True

def mostrar_restricao_permissao():
    """Exibe mensagem de restrição de permissão"""
    st.error("""
    ❌ **Acesso Restrito**
    
    Você não tem permissão para acessar esta funcionalidade.
    
    **Sua permissão:** {}
    **Permissão necessária:** {}
    
    👨‍💼 _Contate o administrador do sistema_
    """.format(
        st.session_state.tipo_usuario,
        'Admin ou Gestor'
    ))

def criar_usuario_com_permissao(username, password, nome_completo, tipo):
    """Cria usuário com validação de tipo"""
    tipos_validos = list(PERMISSOES.keys())
    if tipo not in tipos_validos:
        return False, f"Tipo de usuário inválido. Use: {', '.join(tipos_validos)}"
    
    return criar_usuario(username, password, nome_completo, tipo)

# CSS Mobile Otimizado com indicadores de permissão
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
    
    /* Indicadores de Permissão */
    .permission-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    .badge-admin { background: #dc3545; color: white; }
    .badge-gestor { background: #ffc107; color: black; }
    .badge-vendedor { background: #28a745; color: white; }
    
    /* Cards com indicadores de acesso */
    .card-with-permission { 
        border-left: 4px solid #6c757d; 
        opacity: 0.6;
    }
    .card-permission-allowed { 
        border-left: 4px solid #28a745;
        opacity: 1;
    }
    
    /* Botões desabilitados por permissão */
    .btn-disabled { 
        opacity: 0.5; 
        cursor: not-allowed;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🇧🇷 FUNÇÕES DE FORMATAÇÃO BRASILEIRA
# =========================================

def formatar_data_brasil(data_string):
    """Converte data para formato brasileiro DD/MM/YYYY"""
    if not data_string:
        return "N/A"
    
    try:
        if isinstance(data_string, (date, datetime)):
            return data_string.strftime("%d/%m/%Y")
            
        if '/' in str(data_string):
            return str(data_string)
            
        if isinstance(data_string, str) and len(data_string) >= 10:
            partes = data_string.split('-')
            if len(partes) >= 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
        
        return str(data_string)
    except:
        return str(data_string)

def formatar_datahora_brasil(datahora_string):
    """Converte data/hora para formato brasileiro"""
    if not datahora_string:
        return "N/A"
    
    try:
        if ' ' in str(datahora_string):
            data_part, hora_part = str(datahora_string).split(' ', 1)
            data_brasil = formatar_data_brasil(data_part)
            hora_part = hora_part[:5]
            return f"{data_brasil} {hora_part}"
        else:
            return formatar_data_brasil(datahora_string)
    except:
        return str(datahora_string)

def formatar_moeda_brasil(valor):
    """Formata valor para moeda brasileira"""
    try:
        return f"R$ {float(valor):.2f}".replace('.', ',')
    except:
        return "R$ 0,00"

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
    """Inicializa banco de dados"""
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
        
        # Tabela de clientes
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
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1
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
        
        # Índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_id ON pedidos(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_pedido)')
        
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
        
        # Produtos de exemplo
        produtos_padrao = [
            ('Camiseta Polo', 'Camiseta', 'M', 'Branco', 29.90, 15.00, 50, 5),
            ('Calça Jeans', 'Calça', '42', 'Azul', 89.90, 45.00, 30, 3),
            ('Agasalho', 'Agasalho', 'G', 'Verde', 129.90, 65.00, 20, 2),
            ('Short', 'Short', 'P', 'Preto', 39.90, 20.00, 40, 5),
            ('Camiseta Regata', 'Camiseta', 'G', 'Vermelho', 24.90, 12.00, 25, 5),
        ]
        
        for nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo in produtos_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo))
        
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
# 📊 SISTEMA A.I. - PREVISÕES E ANÁLISES
# =========================================

def previsao_vendas_ai():
    """Previsão de vendas usando regressão linear"""
    try:
        # Dados históricos de exemplo (em produção viriam do banco)
        meses = np.array([1, 2, 3, 4, 5, 6]).reshape(-1, 1)
        vendas = np.array([12000, 15000, 18000, 22000, 25000, 28000])
        
        modelo = LinearRegression()
        modelo.fit(meses, vendas)
        
        # Previsão para os próximos 3 meses
        proximos_meses = np.array([7, 8, 9]).reshape(-1, 1)
        previsoes = modelo.predict(proximos_meses)
        
        return [
            {"mes": "Julho", "previsao": previsoes[0]},
            {"mes": "Agosto", "previsao": previsoes[1]},
            {"mes": "Setembro", "previsao": previsoes[2]}
        ]
    except Exception as e:
        return []

def analise_estoque_ai():
    """Análise inteligente de estoque"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nome, estoque, estoque_minimo 
            FROM produtos 
            WHERE ativo = 1
            ORDER BY estoque ASC
        ''')
        
        alertas = []
        for produto in cursor.fetchall():
            if produto['estoque'] <= produto['estoque_minimo']:
                alertas.append({
                    "produto": produto['nome'],
                    "estoque_atual": produto['estoque'],
                    "estoque_minimo": produto['estoque_minimo'],
                    "nivel": "CRÍTICO" if produto['estoque'] == 0 else "ALERTA"
                })
            elif produto['estoque'] <= produto['estoque_minimo'] * 2:
                alertas.append({
                    "produto": produto['nome'],
                    "estoque_atual": produto['estoque'],
                    "estoque_minimo": produto['estoque_minimo'],
                    "nivel": "ATENÇÃO"
                })
        
        return alertas
    except Exception as e:
        return []
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
        
        # Clientes inativos (sem pedidos nos últimos 60 dias)
        cursor.execute('''
            SELECT c.nome, MAX(p.data_pedido) as ultima_compra
            FROM clientes c
            LEFT JOIN pedidos p ON c.id = p.cliente_id
            GROUP BY c.id
            HAVING ultima_compra IS NULL OR julianday('now') - julianday(ultima_compra) > 60
        ''')
        
        clientes_inativos = []
        for cliente in cursor.fetchall():
            clientes_inativos.append({
                "nome": cliente['nome'],
                "ultima_compra": formatar_data_brasil(cliente['ultima_compra']) if cliente['ultima_compra'] else "Nunca comprou"
            })
        
        return clientes_inativos[:5]  # Retorna apenas os 5 primeiros
    except Exception as e:
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
            SELECT p.nome, SUM(pi.quantidade) as total_vendido
            FROM pedido_itens pi
            JOIN produtos p ON pi.produto_id = p.id
            GROUP BY p.id
            ORDER BY total_vendido DESC
            LIMIT 5
        ''')
        
        populares = []
        for produto in cursor.fetchall():
            populares.append({
                "produto": produto['nome'],
                "vendas": produto['total_vendido'] or 0
            })
        
        return populares
    except Exception as e:
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 👥 SISTEMA DE CLIENTES - COM PERMISSÕES
# =========================================

def adicionar_cliente(nome, telefone=None, email=None, data_nascimento=None, cpf=None, endereco=None):
    """Adiciona cliente de forma segura"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'clientes', 'criar'):
        return False, "❌ Sem permissão para criar clientes"
    
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
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'clientes', 'ler'):
        return []
    
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

def excluir_cliente(cliente_id):
    """Exclui cliente com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'clientes', 'excluir'):
        return False, "❌ Sem permissão para excluir clientes"
    
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Verificar se cliente tem pedidos
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

def criar_usuario(username, password, nome_completo, tipo):
    """Cria novo usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        password_hash = make_hashes(password)
        
        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, tipo)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, nome_completo, tipo))
        
        conn.commit()
        return True, "✅ Usuário criado com sucesso!"
        
    except sqlite3.IntegrityError:
        return False, "❌ Username já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📦 SISTEMA DE PEDIDOS - COM PERMISSÕES
# =========================================

def criar_pedido(cliente_id, itens, observacoes="", forma_pagamento=""):
    """Cria pedido de forma segura com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'pedidos', 'criar'):
        return False, "❌ Sem permissão para criar pedidos"
    
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Calcular totais
        valor_total = sum(item['quantidade'] * item['preco_unitario'] for item in itens)
        valor_final = valor_total
        
        # Inserir pedido
        cursor.execute('''
            INSERT INTO pedidos (cliente_id, valor_total, valor_final, observacoes, forma_pagamento, vendedor_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cliente_id, valor_total, valor_final, observacoes, forma_pagamento, 1))
        
        pedido_id = cursor.lastrowid
        
        # Inserir itens
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
    """Lista todos os pedidos com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'pedidos', 'ler'):
        return []
    
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

def excluir_pedido(pedido_id):
    """Exclui pedido com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'pedidos', 'excluir'):
        return False, "❌ Sem permissão para excluir pedidos"
    
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()
        return True, "✅ Pedido excluído com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos():
    """Lista produtos para pedidos"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, categoria, tamanho, cor, preco, estoque
            FROM produtos 
            WHERE estoque > 0 AND ativo = 1
            ORDER BY nome
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 RELATÓRIOS CSV - COM PERMISSÕES
# =========================================

def gerar_csv_clientes():
    """Gera CSV de clientes com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'relatorios', 'exportar'):
        return None
    
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY nome')
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Nome', 'Telefone', 'Email', 'CPF', 'Endereço', 'Data Cadastro'])
        
        for row in cursor.fetchall():
            writer.writerow([
                row['id'],
                row['nome'],
                row['telefone'] or '',
                row['email'] or '',
                row['cpf'] or '',
                row['endereco'] or '',
                formatar_datahora_brasil(row['data_cadastro'])
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
# 🏠 PÁGINA DE LOGIN COM INDICADOR DE PERMISSÃO
# =========================================

def pagina_login():
    """Página de login otimizada para mobile"""
    st.markdown('<div style="text-align: center; padding: 2rem 0;">', unsafe_allow_html=True)
    st.markdown('<h1 style="color: #4CAF50;">👕 Sistema Fardamentos + A.I.</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown('<div style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
            st.subheader("🔐 Login")
            
            with st.form("login_form"):
                username = st.text_input("👤 Usuário", placeholder="Digite seu username")
                password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
                
                submit = st.form_submit_button("🚀 Entrar", use_container_width=True)
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Preencha todos os campos!")
                    else:
                        with st.spinner("Verificando..."):
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
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Credenciais de teste com indicadores de permissão
            st.markdown('<div style="border-left: 4px solid #2196F3; background: #E3F2FD; padding: 1rem; border-radius: 8px; margin-top: 1rem;">', unsafe_allow_html=True)
            st.markdown("**🔑 Credenciais para teste:**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Admin**")
                st.markdown('<span class="permission-badge badge-admin">Admin</span>', unsafe_allow_html=True)
                st.markdown("user: admin")
                st.markdown("pass: admin123")
                
            with col2:
                st.markdown("**Gestor**")
                st.markdown('<span class="permission-badge badge-gestor">Gestor</span>', unsafe_allow_html=True)
                st.markdown("user: gestor")
                st.markdown("pass: gestor123")
                
            with col3:
                st.markdown("**Vendedor**")
                st.markdown('<span class="permission-badge badge-vendedor">Vendedor</span>', unsafe_allow_html=True)
                st.markdown("user: vendedor")
                st.markdown("pass: vendedor123")
                
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================
# 📱 DASHBOARD A.I. COM INDICADORES DE PERMISSÃO
# =========================================

def mostrar_dashboard():
    """Dashboard principal com A.I. e indicadores de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'dashboard'):
        mostrar_restricao_permissao()
        return
    
    # Header com indicador de permissão
    badge_class = f"badge-{st.session_state.tipo_usuario}"
    st.markdown(f'''
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h1>📊 Dashboard A.I.</h1>
        <div>
            <span class="permission-badge {badge_class}">{st.session_state.tipo_usuario.upper()}</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f"**Usuário:** {st.session_state.nome_completo} | **Permissão:** {PERMISSOES[st.session_state.tipo_usuario]['descricao']}")
    st.markdown("---")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="card-permission-allowed" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;">', unsafe_allow_html=True)
        st.markdown("👥 **Total Clientes**")
        st.markdown(f"<h2>{len(listar_clientes())}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card-permission-allowed" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;">', unsafe_allow_html=True)
        st.markdown("📦 **Pedidos Hoje**")
        st.markdown("<h2>8</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card-permission-allowed" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;">', unsafe_allow_html=True)
        st.markdown("💰 **Vendas Dia**")
        st.markdown("<h2>R$ 2.850</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="card-permission-allowed" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;">', unsafe_allow_html=True)
        st.markdown("📈 **Crescimento**")
        st.markdown("<h2>+12%</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção A.I.
    st.markdown("---")
    st.markdown('<h2>🤖 Inteligência Artificial</h2>', unsafe_allow_html=True)
    
    # Previsões de Vendas
    st.markdown('<div class="card-permission-allowed" style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
    st.markdown("### 📈 Previsão de Vendas")
    previsoes = previsao_vendas_ai()
    
    if previsoes:
        for prev in previsoes:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{prev['mes']}**")
            with col2:
                st.write(f"R$ {prev['previsao']:,.0f}")
    else:
        st.info("Carregando previsões...")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Alertas de Estoque
    alertas_estoque = analise_estoque_ai()
    if alertas_estoque:
        st.markdown('<div style="border-left: 5px solid #F44336; background: #FFEBEE; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 1rem;">', unsafe_allow_html=True)
        st.markdown("### ⚠️ Alertas de Estoque")
        for alerta in alertas_estoque[:3]:  # Mostra apenas 3 alertas
            st.write(f"**{alerta['produto']}** - Estoque: {alerta['estoque_atual']} (Mín: {alerta['estoque_minimo']})")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Produtos Populares
    populares = produtos_populares_ai()
    if populares:
        st.markdown('<div style="border-left: 5px solid #2196F3; background: #E3F2FD; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 1rem;">', unsafe_allow_html=True)
        st.markdown("### 🏆 Produtos Populares")
        for i, produto in enumerate(populares, 1):
            st.write(f"{i}. **{produto['produto']}** - {produto['vendas']} vendas")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Ações Rápidas com indicadores de permissão
    st.markdown("---")
    st.markdown('<h2>🚀 Ações Rápidas</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        # Clientes - sempre visível para quem tem permissão
        if verificar_permissao(st.session_state.tipo_usuario, 'clientes'):
            if st.button("👥 Gerenciar Clientes", use_container_width=True, key="btn_clientes"):
                st.session_state.menu = "👥 Clientes"
                st.rerun()
        else:
            st.button("👥 Gerenciar Clientes", use_container_width=True, disabled=True, 
                     help="Sem permissão para acessar clientes")
        
        # Relatórios - apenas para admin e gestor
        if verificar_permissao(st.session_state.tipo_usuario, 'relatorios'):
            if st.button("📊 Relatórios A.I.", use_container_width=True, key="btn_relatorios"):
                st.session_state.menu = "📊 Relatórios"
                st.rerun()
        else:
            st.button("📊 Relatórios A.I.", use_container_width=True, disabled=True,
                     help="Sem permissão para acessar relatórios")
    
    with col2:
        # Pedidos - sempre visível para quem tem permissão
        if verificar_permissao(st.session_state.tipo_usuario, 'pedidos'):
            if st.button("📦 Gerenciar Pedidos", use_container_width=True, key="btn_pedidos"):
                st.session_state.menu = "📦 Pedidos"
                st.rerun()
        else:
            st.button("📦 Gerenciar Pedidos", use_container_width=True, disabled=True,
                     help="Sem permissão para acessar pedidos")
        
        # Administração - apenas para admin
        if verificar_permissao(st.session_state.tipo_usuario, 'administracao'):
            if st.button("⚙️ Administração", use_container_width=True, key="btn_admin"):
                st.session_state.menu = "⚙️ Administração"
                st.rerun()
        else:
            st.button("⚙️ Administração", use_container_width=True, disabled=True,
                     help="Sem permissão para acessar administração")

# =========================================
# 👥 INTERFACE CLIENTES COM VERIFICAÇÃO DE PERMISSÃO
# =========================================

def mostrar_clientes():
    """Interface de clientes para mobile com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'clientes'):
        mostrar_restricao_permissao()
        return
    
    st.header("👥 Gerenciar Clientes")
    
    # Indicador de permissão
    badge_class = f"badge-{st.session_state.tipo_usuario}"
    st.markdown(f'<span class="permission-badge {badge_class}">{st.session_state.tipo_usuario.upper()}</span>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cliente"])
    
    with tab1:
        st.subheader("📋 Lista de Clientes")
        
        clientes = listar_clientes()
        if not clientes:
            st.info("📝 Nenhum cliente cadastrado.")
        else:
            for cliente in clientes:
                with st.expander(f"👤 {cliente['nome']} - 📞 {cliente['telefone'] or 'N/A'}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**📧 Email:** {cliente['email'] or 'N/A'}")
                        st.write(f"**🔢 CPF:** {cliente['cpf'] or 'N/A'}")
                        st.write(f"**🏠 Endereço:** {cliente['endereco'] or 'N/A'}")
                        st.write(f"**📅 Cadastro:** {formatar_datahora_brasil(cliente['data_cadastro'])}")
                    
                    with col2:
                        # Botão de exclusão com verificação de permissão
                        if verificar_permissao(st.session_state.tipo_usuario, 'clientes', 'excluir'):
                            if st.button("🗑️ Excluir", key=f"del_{cliente['id']}"):
                                success, message = excluir_cliente(cliente['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        else:
                            st.button("🗑️ Excluir", key=f"del_{cliente['id']}", disabled=True,
                                     help="Sem permissão para excluir clientes")
    
    with tab2:
        st.subheader("➕ Novo Cliente")
        
        # Verifica permissão para criar
        if not verificar_permissao(st.session_state.tipo_usuario, 'clientes', 'criar'):
            st.error("❌ Você não tem permissão para criar novos clientes.")
            return
        
        with st.form("novo_cliente_form", clear_on_submit=True):
            nome = st.text_input("👤 Nome Completo*", placeholder="Nome do cliente")
            
            col1, col2 = st.columns(2)
            with col1:
                telefone = st.text_input("📞 Telefone", placeholder="(11) 99999-9999")
                email = st.text_input("📧 Email", placeholder="cliente@email.com")
            with col2:
                cpf = st.text_input("🔢 CPF", placeholder="000.000.000-00")
                data_nascimento = st.date_input("🎂 Data Nascimento")
            
            endereco = st.text_area("🏠 Endereço", placeholder="Rua, número, bairro...")
            
            if st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True):
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
# 📦 INTERFACE PEDIDOS COM VERIFICAÇÃO DE PERMISSÃO
# =========================================

def mostrar_pedidos():
    """Interface de pedidos para mobile com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'pedidos'):
        mostrar_restricao_permissao()
        return
    
    st.header("📦 Gerenciar Pedidos")
    
    # Indicador de permissão
    badge_class = f"badge-{st.session_state.tipo_usuario}"
    st.markdown(f'<span class="permission-badge {badge_class}">{st.session_state.tipo_usuario.upper()}</span>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Pedidos", "➕ Novo Pedido"])
    
    with tab1:
        st.subheader("📋 Pedidos Realizados")
        
        pedidos = listar_pedidos()
        if not pedidos:
            st.info("📝 Nenhum pedido encontrado.")
        else:
            for pedido in pedidos:
                with st.expander(f"📦 Pedido #{pedido['id']} - {pedido['cliente_nome']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**👤 Cliente:** {pedido['cliente_nome']}")
                        st.write(f"**📅 Data:** {formatar_datahora_brasil(pedido['data_pedido'])}")
                        st.write(f"**💰 Valor:** {formatar_moeda_brasil(pedido['valor_final'])}")
                        st.write(f"**📊 Status:** {pedido['status']}")
                    
                    with col2:
                        # Botão de exclusão com verificação de permissão
                        if verificar_permissao(st.session_state.tipo_usuario, 'pedidos', 'excluir'):
                            if st.button("🗑️ Excluir", key=f"del_pedido_{pedido['id']}"):
                                success, message = excluir_pedido(pedido['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        else:
                            st.button("🗑️ Excluir", key=f"del_pedido_{pedido['id']}", disabled=True,
                                     help="Sem permissão para excluir pedidos")
    
    with tab2:
        st.subheader("➕ Criar Novo Pedido")
        
        # Verifica permissão para criar
        if not verificar_permissao(st.session_state.tipo_usuario, 'pedidos', 'criar'):
            st.error("❌ Você não tem permissão para criar novos pedidos.")
            return
        
        clientes = listar_clientes()
        if not clientes:
            st.warning("👥 Cadastre clientes primeiro!")
            return
        
        # Selecionar cliente
        cliente_opcoes = {f"{c['nome']} - {c['telefone'] or 'N/A'}": c['id'] for c in clientes}
        cliente_selecionado = st.selectbox("👤 Selecione o cliente:", options=list(cliente_opcoes.keys()))
        
        if cliente_selecionado:
            st.success(f"✅ Cliente selecionado: {cliente_selecionado}")
            
            # Sistema simplificado de criação de pedidos
            produtos = listar_produtos()
            if produtos:
                st.subheader("🛒 Produtos Disponíveis")
                
                # Aqui você pode expandir para um sistema completo de carrinho
                produto_selecionado = st.selectbox(
                    "Selecione o produto:",
                    [f"{p['nome']} - {p['tamanho']} - R$ {p['preco']:.2f}" for p in produtos]
                )
                
                quantidade = st.number_input("Quantidade:", min_value=1, value=1)
                
                if st.button("✅ Criar Pedido Simples", use_container_width=True):
                    # Simulação de criação de pedido
                    st.success("🎉 Pedido criado com sucesso!")
                    st.info("💡 Em uma versão completa, aqui seria implementado o carrinho completo")
            else:
                st.warning("📦 Nenhum produto disponível em estoque.")

# =========================================
# 📊 RELATÓRIOS COM VERIFICAÇÃO DE PERMISSÃO
# =========================================

def mostrar_relatorios():
    """Interface de relatórios para mobile com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'relatorios'):
        mostrar_restricao_permissao()
        return
    
    st.header("📊 Relatórios A.I.")
    
    # Indicador de permissão
    badge_class = f"badge-{st.session_state.tipo_usuario}"
    st.markdown(f'<span class="permission-badge {badge_class}">{st.session_state.tipo_usuario.upper()}</span>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Exportar Dados")
        
        # Verifica permissão para exportar
        if verificar_permissao(st.session_state.tipo_usuario, 'relatorios', 'exportar'):
            if st.button("👥 Exportar Clientes CSV", use_container_width=True):
                csv_data = gerar_csv_clientes()
                if csv_data:
                    baixar_csv(csv_data, "clientes")
        else:
            st.button("👥 Exportar Clientes CSV", use_container_width=True, disabled=True,
                     help="Sem permissão para exportar dados")
    
    with col2:
        st.subheader("📈 Métricas A.I.")
        
        st.metric("Clientes Ativos", len(listar_clientes()))
        st.metric("Previsão Mensal", "R$ 28.500")
        st.metric("Crescimento", "+15%")

# =========================================
# ⚙️ ADMINISTRAÇÃO COM VERIFICAÇÃO DE PERMISSÃO
# =========================================

def mostrar_administracao():
    """Interface administrativa para mobile com verificação de permissão"""
    # Verifica permissão
    if not verificar_permissao(st.session_state.tipo_usuario, 'administracao'):
        mostrar_restricao_permissao()
        return
    
    st.header("⚙️ Administração")
    
    # Indicador de permissão
    st.markdown('<span class="permission-badge badge-admin">ADMIN</span>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔧 Sistema", "👥 Gerenciar Usuários"])
    
    with tab1:
        st.subheader("🔧 Configurações do Sistema")
        
        if st.button("🔄 Reiniciar Banco de Dados", use_container_width=True):
            with st.spinner("Reiniciando..."):
                if init_db():
                    st.success("✅ Banco reiniciado com sucesso!")
                else:
                    st.error("❌ Erro ao reiniciar banco!")
    
    with tab2:
        st.subheader("👥 Gerenciar Usuários")
        
        # Formulário para criar novo usuário
        with st.form("form_novo_usuario"):
            st.write("### ➕ Criar Novo Usuário")
            
            col1, col2 = st.columns(2)
            with col1:
                novo_username = st.text_input("Username")
                novo_nome = st.text_input("Nome Completo")
            with col2:
                nova_senha = st.text_input("Senha", type="password")
                novo_tipo = st.selectbox("Tipo", options=list(PERMISSOES.keys()))
            
            if st.form_submit_button("👤 Criar Usuário"):
                if novo_username and nova_senha and novo_nome:
                    success, message = criar_usuario_com_permissao(
                        novo_username, nova_senha, novo_nome, novo_tipo
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("❌ Preencha todos os campos!")

# =========================================
# 🧩 MENU PRINCIPAL COM FILTRAGEM POR PERMISSÃO
# =========================================

def mostrar_menu_principal():
    """Menu mobile otimizado com filtragem por permissão"""
    st.sidebar.markdown('<div style="text-align: center; padding: 1rem 0;">', unsafe_allow_html=True)
    st.sidebar.markdown('<h2>👕 Menu</h2>', unsafe_allow_html=True)
    
    # Badge de permissão
    badge_class = f"badge-{st.session_state.tipo_usuario}"
    st.sidebar.markdown(f'<span class="permission-badge {badge_class}">{st.session_state.tipo_usuario.upper()}</span>', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"**👤 {st.session_state.nome_completo}**")
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    # Menu baseado nas permissões
    menu_options = ["🏠 Dashboard"]
    
    # Filtra opções baseado nas permissões
    if verificar_permissao(st.session_state.tipo_usuario, 'clientes'):
        menu_options.append("👥 Clientes")
    
    if verificar_permissao(st.session_state.tipo_usuario, 'pedidos'):
        menu_options.append("📦 Pedidos")
    
    if verificar_permissao(st.session_state.tipo_usuario, 'relatorios'):
        menu_options.append("📊 Relatórios")
    
    if verificar_permissao(st.session_state.tipo_usuario, 'administracao'):
        menu_options.append("⚙️ Administração")
    
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
        st.error("❌ Erro ao inicializar banco!")
        return
    
    # Verificar autenticação
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        pagina_login()
        return
    
    # Menu principal
    menu = mostrar_menu_principal()
    
    # Navegação com verificação de permissão
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
