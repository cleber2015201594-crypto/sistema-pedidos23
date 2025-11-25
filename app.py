import streamlit as st
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import sqlite3
import csv
from io import StringIO

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gestão",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sistema de Autenticação
def init_db():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  nivel TEXT,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT,
                  telefone TEXT,
                  email TEXT,
                  cpf TEXT UNIQUE,
                  endereco TEXT,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de escolas
    c.execute('''CREATE TABLE IF NOT EXISTS escolas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT,
                  telefone TEXT,
                  email TEXT,
                  endereco TEXT,
                  responsavel TEXT,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de produtos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT,
                  descricao TEXT,
                  preco REAL,
                  custo REAL,
                  estoque_minimo INTEGER,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de estoque por escola
    c.execute('''CREATE TABLE IF NOT EXISTS estoque_escolas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  escola_id INTEGER,
                  produto_id INTEGER,
                  quantidade INTEGER,
                  FOREIGN KEY(escola_id) REFERENCES escolas(id),
                  FOREIGN KEY(produto_id) REFERENCES produtos(id))''')
    
    # Tabela de pedidos
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cliente_id INTEGER,
                  escola_id INTEGER,
                  status TEXT,
                  total REAL,
                  desconto REAL,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                  FOREIGN KEY(escola_id) REFERENCES escolas(id))''')
    
    # Tabela de itens do pedido
    c.execute('''CREATE TABLE IF NOT EXISTS itens_pedido
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pedido_id INTEGER,
                  produto_id INTEGER,
                  quantidade INTEGER,
                  preco_unitario REAL,
                  FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
                  FOREIGN KEY(produto_id) REFERENCES produtos(id))''')
    
    # Inserir usuário admin padrão se não existir
    c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
    if c.fetchone()[0] == 0:
        senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (?, ?, ?)",
                 ('admin', senha_hash, 'admin'))
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and user[2] == hash_password(password):
        return user
    return None

# Funções de Gestão de Clientes
def add_cliente(nome, telefone, email, cpf, endereco):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO clientes (nome, telefone, email, cpf, endereco)
                     VALUES (?, ?, ?, ?, ?)''', (nome, telefone, email, cpf, endereco))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_clientes():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM clientes ORDER BY nome")
    clientes = c.fetchall()
    conn.close()
    return clientes

def update_cliente(cliente_id, nome, telefone, email, cpf, endereco):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''UPDATE clientes SET nome=?, telefone=?, email=?, cpf=?, endereco=?
                 WHERE id=?''', (nome, telefone, email, cpf, endereco, cliente_id))
    conn.commit()
    conn.close()

def delete_cliente(cliente_id):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    conn.commit()
    conn.close()

# Funções de Gestão de Escolas
def add_escola(nome, telefone, email, endereco, responsavel):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''INSERT INTO escolas (nome, telefone, email, endereco, responsavel)
                 VALUES (?, ?, ?, ?, ?)''', (nome, telefone, email, endereco, responsavel))
    conn.commit()
    conn.close()

def get_escolas():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM escolas ORDER BY nome")
    escolas = c.fetchall()
    conn.close()
    return escolas

# Funções de Gestão de Produtos
def add_produto(nome, descricao, preco, custo, estoque_minimo):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''INSERT INTO produtos (nome, descricao, preco, custo, estoque_minimo)
                 VALUES (?, ?, ?, ?, ?)''', (nome, descricao, preco, custo, estoque_minimo))
    conn.commit()
    conn.close()

def get_produtos():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM produtos ORDER BY nome")
    produtos = c.fetchall()
    conn.close()
    return produtos

# Funções de Gestão de Pedidos
def add_pedido(cliente_id, escola_id, itens, desconto=0):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Calcular total
    total = sum(item['quantidade'] * item['preco'] for item in itens)
    total_com_desconto = total - (total * desconto / 100)
    
    # Inserir pedido
    c.execute('''INSERT INTO pedidos (cliente_id, escola_id, status, total, desconto)
                 VALUES (?, ?, ?, ?, ?)''', 
              (cliente_id, escola_id, 'Pendente', total_com_desconto, desconto))
    
    pedido_id = c.lastrowid
    
    # Inserir itens do pedido
    for item in itens:
        c.execute('''INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)
                     VALUES (?, ?, ?, ?)''', 
                  (pedido_id, item['produto_id'], item['quantidade'], item['preco']))
    
    conn.commit()
    conn.close()
    return pedido_id

def get_pedidos():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome 
                 FROM pedidos p
                 LEFT JOIN clientes c ON p.cliente_id = c.id
                 LEFT JOIN escolas e ON p.escola_id = e.id
                 ORDER BY p.criado_em DESC''')
    pedidos = c.fetchall()
    conn.close()
    return pedidos

# Sistema de IA - Previsões Simples
def previsao_vendas():
    # Simulação de previsão de vendas
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
    vendas = [12000, 15000, 18000, 22000, 25000, 29000]  # Tendência de crescimento
    
    fig = px.line(x=meses, y=vendas, title='Previsão de Vendas - Próximos 6 Meses')
    fig.update_layout(xaxis_title='Mês', yaxis_title='Vendas (R$)')
    return fig

def alertas_estoque():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''SELECT p.nome, p.estoque_minimo, COALESCE(SUM(e.quantidade), 0) as estoque_atual
                 FROM produtos p
                 LEFT JOIN estoque_escolas e ON p.id = e.produto_id
                 GROUP BY p.id
                 HAVING estoque_atual <= p.estoque_minimo''')
    alertas = c.fetchall()
    conn.close()
    return alertas

# Interface Principal
def main():
    init_db()
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.user:
        show_login()
    else:
        show_main_app()

def show_login():
    st.title("🔐 Sistema de Gestão - Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            user = verify_login(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def show_main_app():
    st.sidebar.title(f"👋 Bem-vindo, {st.session_state.user[1]}")
    
    # Menu lateral baseado no nível de usuário
    menu_options = ["📊 Dashboard", "👥 Gestão de Clientes", "🏫 Gestão de Escolas", 
                   "📦 Sistema de Pedidos", "📈 Relatórios", "🤖 Sistema A.I."]
    
    if st.session_state.user[3] == 'admin':
        menu_options.append("🔐 Administração")
    
    choice = st.sidebar.selectbox("Navegação", menu_options)
    
    if choice == "📊 Dashboard":
        show_dashboard()
    elif choice == "👥 Gestão de Clientes":
        show_client_management()
    elif choice == "🏫 Gestão de Escolas":
        show_school_management()
    elif choice == "📦 Sistema de Pedidos":
        show_order_management()
    elif choice == "📈 Relatórios":
        show_reports()
    elif choice == "🤖 Sistema A.I.":
        show_ai_system()
    elif choice == "🔐 Administração":
        show_admin_panel()
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.user = None
        st.rerun()

def show_dashboard():
    st.title("📊 Dashboard Principal")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        clientes = get_clientes()
        st.metric("Total de Clientes", len(clientes))
    
    with col2:
        escolas = get_escolas()
        st.metric("Escolas Parceiras", len(escolas))
    
    with col3:
        pedidos = get_pedidos()
        st.metric("Pedidos Realizados", len(pedidos))
    
    with col4:
        total_vendas = sum(pedido[4] for pedido in pedidos)
        st.metric("Faturamento Total", f"R$ {total_vendas:,.2f}")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(previsao_vendas(), use_container_width=True)
    
    with col2:
        # Gráfico de status dos pedidos
        status_count = {}
        for pedido in pedidos:
            status = pedido[3]
            status_count[status] = status_count.get(status, 0) + 1
        
        if status_count:
            fig = px.pie(values=list(status_count.values()), 
                        names=list(status_count.keys()),
                        title="Status dos Pedidos")
            st.plotly_chart(fig, use_container_width=True)

def show_client_management():
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Cliente", "Lista de Clientes", "Buscar/Editar"])
    
    with tab1:
        st.subheader("Novo Cliente")
        with st.form("novo_cliente"):
            nome = st.text_input("Nome Completo")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            cpf = st.text_input("CPF")
            endereco = st.text_area("Endereço")
            
            if st.form_submit_button("Cadastrar Cliente"):
                if add_cliente(nome, telefone, email, cpf, endereco):
                    st.success("Cliente cadastrado com sucesso!")
                else:
                    st.error("Erro: CPF já cadastrado no sistema")
    
    with tab2:
        st.subheader("Lista de Clientes")
        clientes = get_clientes()
        
        for cliente in clientes:
            with st.expander(f"{cliente[1]} - {cliente[4]}"):
                st.write(f"**Telefone:** {cliente[2]}")
                st.write(f"**Email:** {cliente[3]}")
                st.write(f"**Endereço:** {cliente[5]}")
                
                if st.button(f"Excluir", key=f"del_{cliente[0]}"):
                    delete_cliente(cliente[0])
                    st.rerun()
    
    with tab3:
        st.subheader("Buscar e Editar Clientes")
        search_term = st.text_input("Buscar por nome ou CPF")
        
        if search_term:
            clientes_filtrados = [c for c in clientes if search_term.lower() in c[1].lower() or search_term in c[4]]
            
            for cliente in clientes_filtrados:
                with st.form(f"edit_{cliente[0]}"):
                    st.write(f"Editando: {cliente[1]}")
                    nome = st.text_input("Nome", value=cliente[1], key=f"nome_{cliente[0]}")
                    telefone = st.text_input("Telefone", value=cliente[2], key=f"tel_{cliente[0]}")
                    email = st.text_input("Email", value=cliente[3], key=f"email_{cliente[0]}")
                    cpf = st.text_input("CPF", value=cliente[4], key=f"cpf_{cliente[0]}")
                    endereco = st.text_area("Endereço", value=cliente[5], key=f"end_{cliente[0]}")
                    
                    if st.form_submit_button("Atualizar"):
                        update_cliente(cliente[0], nome, telefone, email, cpf, endereco)
                        st.success("Cliente atualizado!")
                        st.rerun()

def show_school_management():
    st.title("🏫 Gestão de Escolas")
    
    tab1, tab2 = st.tabs(["Cadastrar Escola", "Lista de Escolas"])
    
    with tab1:
        st.subheader("Nova Escola Parceira")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            endereco = st.text_area("Endereço")
            responsavel = st.text_input("Responsável")
            
            if st.form_submit_button("Cadastrar Escola"):
                add_escola(nome, telefone, email, endereco, responsavel)
                st.success("Escola cadastrada com sucesso!")
    
    with tab2:
        st.subheader("Escolas Parceiras")
        escolas = get_escolas()
        
        for escola in escolas:
            with st.expander(f"{escola[1]}"):
                st.write(f"**Telefone:** {escola[2]}")
                st.write(f"**Email:** {escola[3]}")
                st.write(f"**Endereço:** {escola[4]}")
                st.write(f"**Responsável:** {escola[5]}")

def show_order_management():
    st.title("📦 Sistema de Pedidos")
    
    tab1, tab2 = st.tabs(["Novo Pedido", "Histórico de Pedidos"])
    
    with tab1:
        st.subheader("Criar Novo Pedido")
        
        clientes = get_clientes()
        escolas = get_escolas()
        produtos = get_produtos()
        
        with st.form("novo_pedido"):
            col1, col2 = st.columns(2)
            
            with col1:
                cliente_selecionado = st.selectbox("Cliente", 
                                                  [f"{c[0]} - {c[1]}" for c in clientes])
                escola_selecionada = st.selectbox("Escola", 
                                                 [f"{e[0]} - {e[1]}" for e in escolas])
                desconto = st.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=0.0)
            
            st.subheader("Itens do Pedido")
            
            itens = []
            for i in range(3):  # Permite até 3 itens inicialmente
                col1, col2, col3 = st.columns(3)
                with col1:
                    produto = st.selectbox(f"Produto {i+1}", 
                                          [f"{p[0]} - {p[1]}" for p in produtos],
                                          key=f"prod_{i}")
                with col2:
                    quantidade = st.number_input(f"Quantidade {i+1}", min_value=0, value=0, key=f"qtd_{i}")
                with col3:
                    preco = st.number_input(f"Preço {i+1}", min_value=0.0, value=0.0, key=f"preco_{i}")
                
                if produto and quantidade > 0:
                    produto_id = int(produto.split(' - ')[0])
                    itens.append({
                        'produto_id': produto_id,
                        'quantidade': quantidade,
                        'preco': preco
                    })
            
            if st.form_submit_button("Criar Pedido"):
                cliente_id = int(cliente_selecionado.split(' - ')[0])
                escola_id = int(escola_selecionada.split(' - ')[0])
                
                pedido_id = add_pedido(cliente_id, escola_id, itens, desconto)
                st.success(f"Pedido #{pedido_id} criado com sucesso!")
    
    with tab2:
        st.subheader("Histórico de Pedidos")
        pedidos = get_pedidos()
        
        for pedido in pedidos:
            with st.expander(f"Pedido #{pedido[0]} - {pedido[8]} - R$ {pedido[4]:.2f}"):
                st.write(f"**Cliente:** {pedido[6]}")
                st.write(f"**Escola:** {pedido[7]}")
                st.write(f"**Status:** {pedido[3]}")
                st.write(f"**Total:** R$ {pedido[4]:.2f}")
                st.write(f"**Desconto:** {pedido[5]}%")
                st.write(f"**Data:** {pedido[6]}")

def show_reports():
    st.title("📈 Relatórios e Análises")
    
    # Exportação de dados
    st.subheader("Exportar Dados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Exportar Clientes CSV"):
            clientes = get_clientes()
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Nome', 'Telefone', 'Email', 'CPF', 'Endereço'])
            writer.writerows(clientes)
            st.download_button("Baixar CSV", output.getvalue(), "clientes.csv")
    
    with col2:
        if st.button("Exportar Pedidos CSV"):
            pedidos = get_pedidos()
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Cliente_ID', 'Escola_ID', 'Status', 'Total', 'Desconto', 'Data'])
            writer.writerows(pedidos)
            st.download_button("Baixar CSV", output.getvalue(), "pedidos.csv")
    
    with col3:
        if st.button("Exportar Escolas CSV"):
            escolas = get_escolas()
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Nome', 'Telefone', 'Email', 'Endereço', 'Responsável'])
            writer.writerows(escolas)
            st.download_button("Baixar CSV", output.getvalue(), "escolas.csv")

def show_ai_system():
    st.title("🤖 Sistema A.I. Inteligente")
    
    tab1, tab2 = st.tabs(["📈 Previsões de Vendas", "⚠️ Alertas Automáticos"])
    
    with tab1:
        st.subheader("Previsões de Vendas")
        st.plotly_chart(previsao_vendas(), use_container_width=True)
        
        # Análise de tendências
        st.subheader("Análise de Tendências")
        st.info("""
        **Insights da IA:**
        - Tendência de crescimento: 15% ao mês
        - Produtos mais populares: Uniformes escolares
        - Período de pico: Início do ano letivo
        """)
    
    with tab2:
        st.subheader("Alertas de Estoque")
        alertas = alertas_estoque()
        
        if alertas:
            for alerta in alertas:
                st.error(f"⚠️ {alerta[0]} - Estoque: {alerta[2]} (Mínimo: {alerta[1]})")
        else:
            st.success("✅ Nenhum alerta de estoque no momento")

def show_admin_panel():
    if st.session_state.user[3] != 'admin':
        st.error("Acesso negado!")
        return
        
    st.title("🔐 Painel de Administração")
    
    tab1, tab2 = st.tabs(["Gerenciar Usuários", "Backup de Dados"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        # Implementar CRUD de usuários aqui
    
    with tab2:
        st.subheader("Backup de Dados")
        
        if st.button("Gerar Backup Completo"):
            # Criar backup de todas as tabelas
            conn = sqlite3.connect('gestao.db')
            backup_data = {}
            
            tables = ['usuarios', 'clientes', 'escolas', 'produtos', 'pedidos', 'itens_pedido']
            for table in tables:
                c = conn.cursor()
                c.execute(f"SELECT * FROM {table}")
                backup_data[table] = c.fetchall()
            
            conn.close()
            
            # Salvar como JSON
            backup_json = json.dumps(backup_data, indent=2)
            st.download_button("Baixar Backup", backup_json, "backup_sistema.json")

if __name__ == "__main__":
    main()
