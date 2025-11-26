import streamlit as st
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import csv
from io import StringIO
import pytz
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import urllib.parse

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gestão",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração do banco de dados
def get_database_url():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        return 'sqlite:///gestao.db'

# Criar engine do SQLAlchemy
engine = create_engine(get_database_url())
Base = declarative_base()

# Definir modelos
class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    nivel = Column(String(20), nullable=False)
    criado_em = Column(DateTime, default=datetime.now)

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    telefone = Column(String(20))
    email = Column(String(100))
    cpf = Column(String(20))
    endereco = Column(Text)
    criado_em = Column(DateTime, default=datetime.now)

class Escola(Base):
    __tablename__ = 'escolas'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    telefone = Column(String(20))
    email = Column(String(100))
    endereco = Column(Text)
    responsavel = Column(String(100))
    criado_em = Column(DateTime, default=datetime.now)

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    preco = Column(Float, nullable=False)
    custo = Column(Float)
    estoque_minimo = Column(Integer, default=5)
    tamanho = Column(String(10))
    criado_em = Column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint('nome', 'tamanho', name='_nome_tamanho_uc'),)

class EstoqueEscola(Base):
    __tablename__ = 'estoque_escolas'
    id = Column(Integer, primary_key=True)
    escola_id = Column(Integer, ForeignKey('escolas.id'))
    produto_id = Column(Integer, ForeignKey('produtos.id'))
    quantidade = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint('escola_id', 'produto_id', name='_escola_produto_uc'),)

class Pedido(Base):
    __tablename__ = 'pedidos'
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'))
    escola_id = Column(Integer, ForeignKey('escolas.id'))
    status = Column(String(20), default='Pendente')
    total = Column(Float)
    desconto = Column(Float, default=0)
    custo_total = Column(Float)
    lucro_total = Column(Float)
    margem_lucro = Column(Float)
    criado_em = Column(DateTime, default=datetime.now)

class ItemPedido(Base):
    __tablename__ = 'itens_pedido'
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey('pedidos.id'))
    produto_id = Column(Integer, ForeignKey('produtos.id'))
    quantidade = Column(Integer)
    preco_unitario = Column(Float)
    custo_unitario = Column(Float)
    lucro_unitario = Column(Float)
    margem_lucro = Column(Float)

# Criar tabelas
Base.metadata.create_all(engine)

# Criar session
Session = sessionmaker(bind=engine)

# Função para obter data/hora do Brasil
def get_brasil_datetime():
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    return datetime.now(tz_brasil)

def format_date_br(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            return dt
    return dt.strftime("%d/%m/%Y %H:%M")

# Sistema de Autenticação
def init_db():
    session = Session()
    try:
        # Verificar se usuário admin existe
        admin = session.query(Usuario).filter_by(username='admin').first()
        if not admin:
            senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
            admin = Usuario(username='admin', password=senha_hash, nivel='admin')
            session.add(admin)
            session.commit()
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {e}")
        session.rollback()
    finally:
        session.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    session = Session()
    try:
        user = session.query(Usuario).filter_by(username=username).first()
        if user and user.password == hash_password(password):
            return user
        return None
    except Exception as e:
        st.error(f"Erro ao verificar login: {e}")
        return None
    finally:
        session.close()

# Funções de Gestão de Clientes
def add_cliente(nome, telefone, email, cpf, endereco):
    session = Session()
    try:
        cliente = Cliente(
            nome=nome,
            telefone=telefone,
            email=email,
            cpf=cpf,
            endereco=endereco
        )
        session.add(cliente)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao cadastrar cliente: {e}")
        return False
    finally:
        session.close()

def get_clientes():
    session = Session()
    try:
        clientes = session.query(Cliente).order_by(Cliente.nome).all()
        return [(c.id, c.nome, c.telefone, c.email, c.cpf, c.endereco, c.criado_em) for c in clientes]
    except Exception as e:
        st.error(f"Erro ao buscar clientes: {e}")
        return []
    finally:
        session.close()

# Funções de Gestão de Escolas
def add_escola(nome, telefone, email, endereco, responsavel):
    session = Session()
    try:
        escola = Escola(
            nome=nome,
            telefone=telefone,
            email=email,
            endereco=endereco,
            responsavel=responsavel
        )
        session.add(escola)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao cadastrar escola: {e}")
        return False
    finally:
        session.close()

def get_escolas():
    session = Session()
    try:
        escolas = session.query(Escola).order_by(Escola.nome).all()
        return [(e.id, e.nome, e.telefone, e.email, e.endereco, e.responsavel, e.criado_em) for e in escolas]
    except Exception as e:
        st.error(f"Erro ao buscar escolas: {e}")
        return []
    finally:
        session.close()

# Funções de Gestão de Produtos
def add_produto(nome, descricao, preco, custo, estoque_minimo, tamanho):
    session = Session()
    try:
        # Verificar se produto já existe
        existente = session.query(Produto).filter_by(nome=nome, tamanho=tamanho).first()
        if existente:
            return False, "Já existe um produto com este nome e tamanho"
        
        produto = Produto(
            nome=nome,
            descricao=descricao,
            preco=preco,
            custo=custo,
            estoque_minimo=estoque_minimo,
            tamanho=tamanho
        )
        session.add(produto)
        session.commit()
        return True, produto.id
    except IntegrityError:
        session.rollback()
        return False, "Já existe um produto com este nome e tamanho"
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao cadastrar produto: {e}")
        return False, str(e)
    finally:
        session.close()

def get_produtos():
    session = Session()
    try:
        produtos = session.query(Produto).order_by(Produto.nome, Produto.tamanho).all()
        return [(p.id, p.nome, p.descricao, p.preco, p.custo, p.estoque_minimo, p.tamanho, p.criado_em) for p in produtos]
    except Exception as e:
        st.error(f"Erro ao buscar produtos: {e}")
        return []
    finally:
        session.close()

# Funções de Gestão de Estoque
def vincular_produto_todas_escolas(produto_id, quantidade_inicial=0):
    session = Session()
    try:
        escolas = get_escolas()
        for escola in escolas:
            # Verificar se já existe
            estoque = session.query(EstoqueEscola).filter_by(
                escola_id=escola[0], produto_id=produto_id
            ).first()
            
            if not estoque:
                novo_estoque = EstoqueEscola(
                    escola_id=escola[0],
                    produto_id=produto_id,
                    quantidade=quantidade_inicial
                )
                session.add(novo_estoque)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao vincular produto: {e}")
        return False
    finally:
        session.close()

def get_estoque_escola(escola_id):
    session = Session()
    try:
        estoque = session.query(EstoqueEscola, Produto).join(
            Produto, EstoqueEscola.produto_id == Produto.id
        ).filter(EstoqueEscola.escola_id == escola_id).all()
        
        return [(
            e.EstoqueEscola.id, 
            e.Produto.nome, 
            e.Produto.tamanho, 
            e.EstoqueEscola.quantidade, 
            e.Produto.estoque_minimo,
            e.Produto.preco,
            e.Produto.custo,
            e.Produto.id
        ) for e in estoque]
    except Exception as e:
        st.error(f"Erro ao buscar estoque: {e}")
        return []
    finally:
        session.close()

def update_estoque_escola(escola_id, produto_id, quantidade):
    session = Session()
    try:
        estoque = session.query(EstoqueEscola).filter_by(
            escola_id=escola_id, produto_id=produto_id
        ).first()
        
        if estoque:
            estoque.quantidade = quantidade
        else:
            estoque = EstoqueEscola(
                escola_id=escola_id,
                produto_id=produto_id,
                quantidade=quantidade
            )
            session.add(estoque)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao atualizar estoque: {e}")
        return False
    finally:
        session.close()

# Funções de Gestão de Pedidos
def add_pedido(cliente_id, escola_id, itens, desconto=0):
    session = Session()
    try:
        # Calcular totais
        total_venda = sum(item['quantidade'] * item['preco'] for item in itens)
        total_custo = sum(item['quantidade'] * item['custo'] for item in itens)
        total_com_desconto = total_venda - (total_venda * desconto / 100)
        lucro_total = total_com_desconto - total_custo
        margem_lucro = (lucro_total / total_com_desconto * 100) if total_com_desconto > 0 else 0
        
        # Criar pedido
        pedido = Pedido(
            cliente_id=cliente_id,
            escola_id=escola_id,
            total=total_com_desconto,
            desconto=desconto,
            custo_total=total_custo,
            lucro_total=lucro_total,
            margem_lucro=margem_lucro
        )
        session.add(pedido)
        session.flush()  # Para obter o ID do pedido
        
        # Adicionar itens e atualizar estoque
        for item in itens:
            lucro_unitario = item['preco'] - item['custo']
            margem_unitario = (lucro_unitario / item['preco'] * 100) if item['preco'] > 0 else 0
            
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                produto_id=item['produto_id'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco'],
                custo_unitario=item['custo'],
                lucro_unitario=lucro_unitario,
                margem_lucro=margem_unitario
            )
            session.add(item_pedido)
            
            # Atualizar estoque
            estoque = session.query(EstoqueEscola).filter_by(
                escola_id=escola_id, produto_id=item['produto_id']
            ).first()
            
            if estoque:
                estoque.quantidade -= item['quantidade']
        
        session.commit()
        return pedido.id
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao criar pedido: {e}")
        return None
    finally:
        session.close()

def get_pedidos():
    session = Session()
    try:
        pedidos = session.query(Pedido, Cliente, Escola).join(
            Cliente, Pedido.cliente_id == Cliente.id
        ).join(
            Escola, Pedido.escola_id == Escola.id
        ).order_by(Pedido.criado_em.desc()).all()
        
        return [(
            p.Pedido.id, p.Pedido.cliente_id, p.Pedido.escola_id, p.Pedido.status,
            p.Pedido.total, p.Pedido.desconto, p.Pedido.custo_total, p.Pedido.lucro_total,
            p.Pedido.margem_lucro, p.Pedido.criado_em, p.Cliente.nome, p.Escola.nome
        ) for p in pedidos]
    except Exception as e:
        st.error(f"Erro ao buscar pedidos: {e}")
        return []
    finally:
        session.close()

def update_pedido_status(pedido_id, novo_status):
    session = Session()
    try:
        pedido = session.query(Pedido).filter_by(id=pedido_id).first()
        if pedido:
            pedido.status = novo_status
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao atualizar status: {e}")
        return False
    finally:
        session.close()

# Funções de Gestão de Usuários
def add_usuario(username, password, nivel):
    session = Session()
    try:
        senha_hash = hash_password(password)
        usuario = Usuario(
            username=username,
            password=senha_hash,
            nivel=nivel
        )
        session.add(usuario)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao criar usuário: {e}")
        return False
    finally:
        session.close()

def get_usuarios():
    session = Session()
    try:
        usuarios = session.query(Usuario).order_by(Usuario.username).all()
        return [(u.id, u.username, u.nivel, u.criado_em) for u in usuarios]
    except Exception as e:
        st.error(f"Erro ao buscar usuários: {e}")
        return []
    finally:
        session.close()

# Sistema de IA
def previsao_vendas():
    meses = ['Próximo Mês', '2° Mês', '3° Mês', '4° Mês', '5° Mês', '6° Mês']
    vendas = [12000, 15000, 18000, 22000, 25000, 29000]
    return meses, vendas

def alertas_estoque():
    session = Session()
    try:
        alertas = session.query(EstoqueEscola, Produto, Escola).join(
            Produto, EstoqueEscola.produto_id == Produto.id
        ).join(
            Escola, EstoqueEscola.escola_id == Escola.id
        ).filter(EstoqueEscola.quantidade <= Produto.estoque_minimo).all()
        
        return [(
            a.EstoqueEscola.escola_id, a.Escola.nome, a.Produto.nome, a.Produto.tamanho,
            a.EstoqueEscola.quantidade, a.Produto.estoque_minimo
        ) for a in alertas]
    except Exception as e:
        st.error(f"Erro ao buscar alertas: {e}")
        return []
    finally:
        session.close()

# Interface Principal (mantida igual)
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
                st.session_state.user = (user.id, user.username, user.password, user.nivel)
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def show_main_app():
    st.sidebar.title(f"👋 Bem-vindo, {st.session_state.user[1]}")
    st.sidebar.write(f"**Nível:** {st.session_state.user[3]}")
    st.sidebar.write(f"**Data:** {format_date_br(get_brasil_datetime())}")
    
    menu_options = ["📊 Dashboard", "👥 Gestão de Clientes", "🏫 Gestão de Escolas", 
                   "📦 Gestão de Produtos", "📦 Sistema de Pedidos", "📈 Relatórios", "🤖 Sistema A.I."]
    
    if st.session_state.user[3] == 'admin':
        menu_options.append("🔐 Administração")
    
    choice = st.sidebar.selectbox("Navegação", menu_options)
    
    if choice == "📊 Dashboard":
        show_dashboard()
    elif choice == "👥 Gestão de Clientes":
        show_client_management()
    elif choice == "🏫 Gestão de Escolas":
        show_school_management()
    elif choice == "📦 Gestão de Produtos":
        show_product_management()
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

def show_client_management():
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2 = st.tabs(["Cadastrar Cliente", "Lista de Clientes"])
    
    with tab1:
        st.subheader("Novo Cliente")
        with st.form("novo_cliente"):
            nome = st.text_input("Nome Completo *")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            cpf = st.text_input("CPF (Opcional)")
            endereco = st.text_area("Endereço")
            
            if st.form_submit_button("Cadastrar Cliente"):
                if nome:
                    if add_cliente(nome, telefone, email, cpf, endereco):
                        st.success("Cliente cadastrado com sucesso!")
                    else:
                        st.error("Erro ao cadastrar cliente")
                else:
                    st.error("Nome é obrigatório")
    
    with tab2:
        st.subheader("Lista de Clientes")
        clientes = get_clientes()
        
        for cliente in clientes:
            with st.expander(f"{cliente[1]} - {cliente[4] or 'Sem CPF'}"):
                st.write(f"**Telefone:** {cliente[2]}")
                st.write(f"**Email:** {cliente[3]}")
                st.write(f"**Endereço:** {cliente[5]}")
                st.write(f"**Cadastrado em:** {format_date_br(cliente[6])}")

def show_school_management():
    st.title("🏫 Gestão de Escolas")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Escola", "Lista de Escolas", "Estoque por Escola"])
    
    with tab1:
        st.subheader("Nova Escola Parceira")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola *")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            endereco = st.text_area("Endereço")
            responsavel = st.text_input("Responsável")
            
            if st.form_submit_button("Cadastrar Escola"):
                if nome:
                    if add_escola(nome, telefone, email, endereco, responsavel):
                        st.success("Escola cadastrada com sucesso!")
                    else:
                        st.error("Erro ao cadastrar escola")
                else:
                    st.error("Nome da escola é obrigatório")
    
    with tab2:
        st.subheader("Escolas Parceiras")
        escolas = get_escolas()
        
        for escola in escolas:
            with st.expander(f"{escola[1]}"):
                st.write(f"**Telefone:** {escola[2]}")
                st.write(f"**Email:** {escola[3]}")
                st.write(f"**Endereço:** {escola[4]}")
                st.write(f"**Responsável:** {escola[5]}")
                st.write(f"**Cadastrado em:** {format_date_br(escola[6])}")
    
    with tab3:
        st.subheader("Estoque por Escola")
        escolas = get_escolas()
        produtos = get_produtos()
        
        if not escolas:
            st.warning("Nenhuma escola cadastrada. Cadastre uma escola primeiro.")
            return
            
        if not produtos:
            st.warning("Nenhum produto cadastrado. Cadastre produtos primeiro.")
            return
        
        escola_selecionada = st.selectbox("Selecione a Escola", 
                                         [f"{e[0]} - {e[1]}" for e in escolas])
        
        if escola_selecionada:
            escola_id = int(escola_selecionada.split(' - ')[0])
            escola_nome = escola_selecionada.split(' - ')[1]
            
            st.write(f"### Estoque da Escola: {escola_nome}")
            
            estoque = get_estoque_escola(escola_id)
            
            if not estoque:
                st.info("Nenhum produto vinculado a esta escola ainda.")
            else:
                for item in estoque:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{item[1]}** - Tamanho: {item[2]}")
                    with col2:
                        st.write(f"**Estoque:** {item[3]}")
                    with col3:
                        if item[3] <= item[4]:
                            st.error(f"⚠️ Mín: {item[4]}")
                        else:
                            st.success(f"✅ Mín: {item[4]}")
            
            st.markdown("---")
            st.subheader("Ajustar Estoque")
            
            produto_ajuste = st.selectbox("Selecione o Produto", 
                                         [f"{p[0]} - {p[1]} ({p[6]})" for p in produtos])
            
            if produto_ajuste:
                produto_id = int(produto_ajuste.split(' - ')[0])
                
                estoque_atual = 0
                for item in estoque:
                    if item[7] == produto_id:
                        estoque_atual = item[3]
                        break
                
                nova_quantidade = st.number_input("Nova quantidade", 
                                                 min_value=0, 
                                                 value=estoque_atual,
                                                 key=f"ajuste_{produto_id}")
                
                if st.button("Atualizar Estoque", key=f"btn_ajuste_{produto_id}"):
                    if update_estoque_escola(escola_id, produto_id, nova_quantidade):
                        st.success(f"Estoque atualizado para {nova_quantidade}!")
                        st.rerun()

def show_product_management():
    st.title("📦 Gestão de Produtos")
    
    tab1, tab2 = st.tabs(["Cadastrar Produto", "Lista de Produtos"])
    
    with tab1:
        st.subheader("Novo Produto")
        with st.form("novo_produto"):
            nome = st.text_input("Nome do Produto *")
            descricao = st.text_area("Descrição")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                preco = st.number_input("Preço de Venda (R$)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                custo = st.number_input("Custo (R$)", min_value=0.0, value=0.0, step=0.01)
            with col3:
                estoque_minimo = st.number_input("Estoque Mínimo", min_value=0, value=5)
            with col4:
                tamanhos = ["", "PP", "P", "M", "G", "GG", "EXG", "2", "4", "6", "8", "10", "12", "Único"]
                tamanho = st.selectbox("Tamanho *", tamanhos)
            
            escolas = get_escolas()
            if escolas:
                vincular_escolas = st.checkbox("Vincular este produto a todas as escolas automaticamente", value=True)
                estoque_inicial = st.number_input("Estoque inicial nas escolas", min_value=0, value=0)
            else:
                st.warning("Cadastre escolas primeiro para vincular produtos")
                vincular_escolas = False
                estoque_inicial = 0
            
            if st.form_submit_button("Cadastrar Produto"):
                if nome and preco > 0 and tamanho:
                    sucesso, resultado = add_produto(nome, descricao, preco, custo, estoque_minimo, tamanho)
                    
                    if sucesso:
                        st.success("Produto cadastrado com sucesso!")
                        
                        if vincular_escolas and escolas:
                            produto_id = resultado
                            if vincular_produto_todas_escolas(produto_id, estoque_inicial):
                                st.success(f"Produto vinculado automaticamente a {len(escolas)} escolas!")
                        
                        if preco > 0 and custo > 0:
                            margem = ((preco - custo) / preco) * 100
                            st.info(f"Margem de lucro: {margem:.1f}%")
                    else:
                        st.error(resultado)
                else:
                    st.error("Nome, preço e tamanho são obrigatórios")
    
    with tab2:
        st.subheader("Lista de Produtos")
        produtos = get_produtos()
        
        for produto in produtos:
            with st.expander(f"{produto[1]} - Tamanho: {produto[6]} - R$ {produto[3]:.2f}"):
                st.write(f"**Descrição:** {produto[2]}")
                st.write(f"**Preço:** R$ {produto[3]:.2f}")
                st.write(f"**Custo:** R$ {produto[4]:.2f}")
                st.write(f"**Estoque Mínimo:** {produto[5]}")
                
                if produto[3] > 0 and produto[4] > 0:
                    margem = ((produto[3] - produto[4]) / produto[3]) * 100
                    lucro_unitario = produto[3] - produto[4]
                    st.write(f"**Margem:** {margem:.1f}%")
                    st.write(f"**Lucro Unitário:** R$ {lucro_unitario:.2f}")

def show_order_management():
    st.title("📦 Sistema de Pedidos")
    
    tab1, tab2 = st.tabs(["Novo Pedido", "Histórico de Pedidos"])
    
    with tab1:
        st.subheader("Criar Novo Pedido")
        
        clientes = get_clientes()
        escolas = get_escolas()
        produtos = get_produtos()
        
        if not clientes:
            st.warning("Cadastre clientes primeiro para criar pedidos")
            return
            
        if not escolas:
            st.warning("Cadastre escolas primeiro para criar pedidos")
            return
            
        if not produtos:
            st.warning("Cadastre produtos primeiro para criar pedidos")
            return
        
        with st.form("novo_pedido"):
            col1, col2 = st.columns(2)
            
            with col1:
                cliente_selecionado = st.selectbox("Cliente *", 
                                                  [f"{c[0]} - {c[1]}" for c in clientes])
                escola_selecionada = st.selectbox("Escola *", 
                                                 [f"{e[0]} - {e[1]}" for e in escolas])
                desconto = st.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=0.0)
            
            st.subheader("Itens do Pedido")
            
            itens = []
            if escola_selecionada:
                escola_id = int(escola_selecionada.split(' - ')[0])
                estoque_escola = get_estoque_escola(escola_id)
            
            for i in range(3):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    produtos_com_estoque = []
                    for produto in produtos:
                        estoque_disponivel = 0
                        for item in estoque_escola:
                            if item[7] == produto[0]:
                                estoque_disponivel = item[3]
                                break
                        
                        if estoque_disponivel > 0:
                            produtos_com_estoque.append(produto)
                    
                    if produtos_com_estoque:
                        produto_opcoes = [f"{p[0]} - {p[1]} ({p[6]}) - Estoque: {next((item[3] for item in estoque_escola if item[7] == p[0]), 0)}" 
                                         for p in produtos_com_estoque]
                        produto_selecionado = st.selectbox(f"Produto {i+1}", [""] + produto_opcoes, key=f"prod_{i}")
                    else:
                        st.warning("Nenhum produto com estoque")
                        produto_selecionado = None
                
                with col2:
                    if produto_selecionado:
                        produto_id = int(produto_selecionado.split(' - ')[0])
                        estoque_disponivel = next((item[3] for item in estoque_escola if item[7] == produto_id), 0)
                        quantidade = st.number_input(f"Qtd {i+1}", min_value=1, max_value=estoque_disponivel, value=1, key=f"qtd_{i}")
                    else:
                        quantidade = 0
                
                with col3:
                    if produto_selecionado:
                        produto_info = next(p for p in produtos if p[0] == produto_id)
                        preco = st.number_input(f"Preço {i+1}", min_value=0.0, value=float(produto_info[3]), key=f"preco_{i}")
                        custo = produto_info[4]
                    else:
                        preco = 0.0
                        custo = 0.0
                
                with col4:
                    if produto_selecionado and preco > 0 and custo > 0:
                        lucro_unitario = preco - custo
                        margem = (lucro_unitario / preco * 100) if preco > 0 else 0
                        st.write(f"Margem: {margem:.1f}%")
                
                if produto_selecionado and quantidade > 0:
                    itens.append({
                        'produto_id': produto_id,
                        'quantidade': quantidade,
                        'preco': preco,
                        'custo': custo
                    })
            
            if itens:
                st.subheader("Resumo do Pedido")
                total_venda = sum(item['quantidade'] * item['preco'] for item in itens)
                total_custo = sum(item['quantidade'] * item['custo'] for item in itens)
                total_com_desconto = total_venda - (total_venda * desconto / 100)
                lucro_total = total_com_desconto - total_custo
                margem_lucro = (lucro_total / total_com_desconto * 100) if total_com_desconto > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Venda", f"R$ {total_venda:.2f}")
                with col2:
                    st.metric("Total com Desconto", f"R$ {total_com_desconto:.2f}")
                with col3:
                    st.metric("Lucro Total", f"R$ {lucro_total:.2f}")
                with col4:
                    st.metric("Margem", f"{margem_lucro:.1f}%")
            
            if st.form_submit_button("Criar Pedido"):
                if not itens:
                    st.error("Adicione pelo menos um item ao pedido")
                else:
                    cliente_id = int(cliente_selecionado.split(' - ')[0])
                    escola_id = int(escola_selecionada.split(' - ')[0])
                    
                    pedido_id = add_pedido(cliente_id, escola_id, itens, desconto)
                    if pedido_id:
                        st.success(f"Pedido #{pedido_id} criado com sucesso!")
    
    with tab2:
        st.subheader("Histórico de Pedidos")
        pedidos = get_pedidos()
        
        for pedido in pedidos:
            with st.expander(f"Pedido #{pedido[0]} - {pedido[10]} - R$ {pedido[4]:.2f} - {pedido[3]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Cliente:** {pedido[10]}")
                    st.write(f"**Escola:** {pedido[11]}")
                    st.write(f"**Status:** {pedido[3]}")
                    st.write(f"**Data:** {format_date_br(pedido[9])}")
                with col2:
                    st.write(f"**Total:** R$ {pedido[4]:.2f}")
                    st.write(f"**Desconto:** {pedido[5]}%")
                    st.write(f"**Custo Total:** R$ {pedido[6]:.2f}")
                    st.write(f"**Lucro:** R$ {pedido[7]:.2f}")
                    st.write(f"**Margem:** {pedido[8]:.1f}%")
                
                st.write("**Alterar Status:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Confirmar", key=f"confirm_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Confirmado")
                        st.rerun()
                with col2:
                    if st.button("🚚 Enviar", key=f"enviar_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Enviado")
                        st.rerun()
                with col3:
                    if st.button("📦 Entregue", key=f"entregue_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Entregue")
                        st.rerun()
                with col4:
                    if st.button("❌ Cancelar", key=f"cancelar_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Cancelado")
                        st.rerun()

def show_reports():
    st.title("📈 Relatórios e Análises")
    
    tab1, tab2 = st.tabs(["Exportar Dados", "Análise Financeira"])
    
    with tab1:
        st.subheader("Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Exportar Clientes CSV"):
                clientes = get_clientes()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nome', 'Telefone', 'Email', 'CPF', 'Endereço', 'Data_Criacao'])
                for cliente in clientes:
                    writer.writerow(cliente)
                st.download_button("Baixar CSV", output.getvalue(), "clientes.csv", "text/csv")
        
        with col2:
            if st.button("Exportar Pedidos CSV"):
                pedidos = get_pedidos()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Cliente_ID', 'Escola_ID', 'Status', 'Total', 'Desconto', 'Custo_Total', 'Lucro_Total', 'Margem_Lucro', 'Data', 'Cliente_Nome', 'Escola_Nome'])
                for pedido in pedidos:
                    writer.writerow(pedido)
                st.download_button("Baixar CSV", output.getvalue(), "pedidos.csv", "text/csv")
        
        with col3:
            if st.button("Exportar Produtos CSV"):
                produtos = get_produtos()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nome', 'Descricao', 'Preco', 'Custo', 'Estoque_Minimo', 'Tamanho', 'Data_Criacao'])
                for produto in produtos:
                    writer.writerow(produto)
                st.download_button("Baixar CSV", output.getvalue(), "produtos.csv", "text/csv")

def show_ai_system():
    st.title("🤖 Sistema A.I. Inteligente")
    
    tab1, tab2 = st.tabs(["📈 Previsões de Vendas", "⚠️ Alertas Automáticos"])
    
    with tab1:
        st.subheader("Previsões de Vendas")
        meses, vendas = previsao_vendas()
        
        st.write("**Previsão para os próximos 6 meses:**")
        for mes, venda in zip(meses, vendas):
            st.write(f"- **{mes}:** R$ {venda:,.2f}")
            st.progress(min(venda / 50000, 1.0))
    
    with tab2:
        st.subheader("Alertas de Estoque")
        alertas = alertas_estoque()
        
        if alertas:
            for alerta in alertas:
                st.error(f"""
                ⚠️ **ALERTA DE ESTOQUE BAIXO**
                - Escola: {alerta[1]}
                - Produto: {alerta[2]} - Tamanho: {alerta[3]}
                - Estoque atual: {alerta[4]}
                - Mínimo recomendado: {alerta[5]}
                """)
        else:
            st.success("✅ Nenhum alerta de estoque baixo no momento")

def show_admin_panel():
    if st.session_state.user[3] != 'admin':
        st.error("Acesso negado! Apenas administradores podem acessar esta área.")
        return
        
    st.title("🔐 Painel de Administração")
    
    tab1, tab2 = st.tabs(["Gerenciar Usuários", "Backup de Dados"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        
        with st.form("novo_usuario"):
            st.write("**Adicionar Novo Usuário**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                username = st.text_input("Nome de usuário")
            with col2:
                password = st.text_input("Senha", type="password")
            with col3:
                nivel = st.selectbox("Nível", ["admin", "gestor", "vendedor"])
            
            if st.form_submit_button("Criar Usuário"):
                if username and password:
                    if add_usuario(username, password, nivel):
                        st.success(f"Usuário {username} criado com sucesso!")
                    else:
                        st.error("Erro ao criar usuário")
                else:
                    st.error("Nome de usuário e senha são obrigatórios")
        
        st.subheader("Usuários do Sistema")
        usuarios = get_usuarios()
        
        for usuario in usuarios:
            with st.expander(f"{usuario[1]} - {usuario[2]}"):
                st.write(f"ID: {usuario[0]}")
                st.write(f"Nível: {usuario[2]}")
                st.write(f"Criado em: {format_date_br(usuario[3])}")

if __name__ == "__main__":
    main()
