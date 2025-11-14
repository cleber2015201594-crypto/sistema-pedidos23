import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib

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
# 🚀 SISTEMA PRINCIPAL - CORRIGIDO
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

# Inicialização dos dados
if 'pedidos' not in st.session_state:
    st.session_state.pedidos = []
if 'clientes' not in st.session_state:
    st.session_state.clientes = []
if 'produtos' not in st.session_state:
    st.session_state.produtos = []
if 'escolas' not in st.session_state:
    st.session_state.escolas = ["Municipal", "Desperta", "São Tadeu"]
if 'itens_pedido' not in st.session_state:
    st.session_state.itens_pedido = []

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

# Funções auxiliares
def salvar_dados():
    dados = {
        'pedidos': st.session_state.pedidos,
        'clientes': st.session_state.clientes,
        'produtos': st.session_state.produtos
    }
    with open('dados.json', 'w') as f:
        json.dump(dados, f)

def carregar_dados():
    if os.path.exists('dados.json'):
        with open('dados.json', 'r') as f:
            dados = json.load(f)
            st.session_state.pedidos = dados.get('pedidos', [])
            st.session_state.clientes = dados.get('clientes', [])
            st.session_state.produtos = dados.get('produtos', [])
            
            # Garantir que produtos antigos tenham campo escola
            for produto in st.session_state.produtos:
                if 'escola' not in produto:
                    produto['escola'] = "Municipal"  # Valor padrão

def verificar_e_corrigir_dados():
    """Verifica e corrige dados corrompidos no session_state"""
    
    # Verificar pedidos
    pedidos_validos = []
    for pedido in st.session_state.pedidos:
        if isinstance(pedido, dict):
            # Garantir campos obrigatórios
            if 'id' not in pedido:
                pedido['id'] = len(pedidos_validos) + 1
            if 'status' not in pedido:
                pedido['status'] = 'Pendente'
            if 'cliente' not in pedido:
                pedido['cliente'] = 'Cliente Desconhecido'
            if 'escola' not in pedido:
                pedido['escola'] = 'Municipal'
            
            pedidos_validos.append(pedido)
    
    st.session_state.pedidos = pedidos_validos

# Carregar e verificar dados
carregar_dados()
verificar_e_corrigir_dados()

# =========================================
# 🎨 NAVEGAÇÃO SIMPLES E FUNCIONAL
# =========================================

st.sidebar.title("👕 Sistema de Fardamentos")

# Menu na sidebar - SIMPLES E FUNCIONAL
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Fardamentos", "📦 Estoque", "📈 Relatórios"]
if 'menu' not in st.session_state:
    st.session_state.menu = menu_options[0]

menu = st.sidebar.radio("Navegação", menu_options, index=menu_options.index(st.session_state.menu))

# Atualizar menu no session_state
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
# 📱 PÁGINAS DO SISTEMA - CORRIGIDAS
# =========================================

# DASHBOARD - CORRIGIDO
if menu == "📊 Dashboard":
    st.header("🎯 Métricas em Tempo Real")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(st.session_state.pedidos)
        st.metric("Total de Pedidos", total_pedidos)
    
    with col2:
        pedidos_pendentes = len([p for p in st.session_state.pedidos if p.get('status', 'Pendente') == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        clientes_ativos = len(st.session_state.clientes)
        st.metric("Clientes Ativos", clientes_ativos)
    
    with col4:
        produtos_baixo_estoque = len([p for p in st.session_state.produtos if p.get('estoque', 0) < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Ações Rápidas - CORRIGIDO
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True, key="btn_pedido"):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True, key="btn_cliente"):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 Cadastrar Fardamento", use_container_width=True, key="btn_fardamento"):
            st.session_state.menu = "👕 Fardamentos"
            st.rerun()
    
    # Seção de Alertas
    st.header("⚠️ Alertas de Estoque")
    produtos_alerta = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    
    if produtos_alerta:
        for produto in produtos_alerta:
            st.warning(f"🚨 {produto['nome']} - Tamanho: {produto.get('tamanho', 'N/A')} - Estoque: {produto.get('estoque', 0)} unidades")
    else:
        st.success("✅ Nenhum alerta de estoque no momento")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Vendas por Escola")
        if st.session_state.pedidos:
            # Criar dados para gráfico com tratamento seguro
            escolas_data = {}
            for pedido in st.session_state.pedidos:
                escola = pedido.get('escola', 'N/A')
                if escola in escolas_data:
                    escolas_data[escola] += 1
                else:
                    escolas_data[escola] = 1
            
            if escolas_data:
                df_escolas = pd.DataFrame(list(escolas_data.items()), columns=['Escola', 'Quantidade'])
                fig = px.bar(df_escolas, x='Escola', y='Quantidade', title="Vendas por Escola")
                st.plotly_chart(fig)
            else:
                st.info("📋 Nenhum dado para mostrar")
        else:
            st.info("📋 Nenhum pedido cadastrado ainda")
    
    with col2:
        st.subheader("🎯 Status dos Pedidos")
        if st.session_state.pedidos:
            # Criar dados para gráfico com tratamento seguro
            status_data = {}
            for pedido in st.session_state.pedidos:
                status = pedido.get('status', 'Pendente')
                if status in status_data:
                    status_data[status] += 1
                else:
                    status_data[status] = 1
            
            if status_data:
                df_status = pd.DataFrame(list(status_data.items()), columns=['Status', 'Quantidade'])
                fig = px.pie(df_status, values='Quantidade', names='Status', title="Distribuição por Status")
                st.plotly_chart(fig)
            else:
                st.info("📋 Nenhum dado para mostrar")
        else:
            st.info("📋 Nenhum pedido para analisar")

# PEDIDOS - CORRIGIDO
elif menu == "📦 Pedidos":
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Novo Pedido", "📋 Listar Pedidos", "🔄 Alterar Status", "✏️ Editar Pedido"])
    
    with tab1:
        st.header("📝 Novo Pedido de Fardamento")
        
        # Dados do cliente
        if st.session_state.clientes:
            cliente_selecionado = st.selectbox("Cliente", 
                [f"{c['nome']} - {c['escola']}" for c in st.session_state.clientes])
            
            if cliente_selecionado:
                escola_cliente = cliente_selecionado.split(' - ')[1]
                st.success(f"🏫 Escola: {escola_cliente}")
        else:
            st.warning("👥 Cadastre clientes primeiro!")
            cliente_selecionado = None
            escola_cliente = None
        
        # SISTEMA DE MÚLTIPLOS ITENS
        st.subheader("🛒 Itens do Pedido")
        
        # Formulário para adicionar item
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtro por tipo
            tipo_filtro = st.selectbox("🔍 Filtrar por tipo:", 
                ["Todos", "Camisetas", "Calças/Shorts", "Agasalhos"])
            
            produtos_filtrados = st.session_state.produtos
            
            # Aplicar filtro de tipo
            if tipo_filtro != "Todos":
                if tipo_filtro == "Camisetas":
                    produtos_filtrados = [p for p in produtos_filtrados if any(tipo in p['nome'] for tipo in tipos_camisetas)]
                elif tipo_filtro == "Calças/Shorts":
                    produtos_filtrados = [p for p in produtos_filtrados if any(tipo in p['nome'] for tipo in tipos_calcas)]
                elif tipo_filtro == "Agasalhos":
                    produtos_filtrados = [p for p in produtos_filtrados if any(tipo in p['nome'] for tipo in tipos_agasalhos)]
            
            # Filtrar por escola do cliente
            if escola_cliente:
                produtos_filtrados = [p for p in produtos_filtrados if p.get('escola') == escola_cliente]
            
            produtos_disponiveis = [p for p in produtos_filtrados if p.get('estoque', 0) > 0]
        
        with col2:
            if produtos_disponiveis and cliente_selecionado:
                produto_selecionado = st.selectbox("👕 Selecione o fardamento", 
                    [f"{p['nome']} - Tamanho: {p.get('tamanho', 'Único')} - Cor: {p.get('cor', 'N/A')} - R${p['preco']:.2f} - Estoque: {p.get('estoque', 0)}" 
                     for p in produtos_disponiveis])
            else:
                if not cliente_selecionado:
                    st.info("👥 Selecione um cliente primeiro")
                else:
                    st.error("❌ Nenhum fardamento disponível!")
                produto_selecionado = None
        
        with col3:
            quantidade_item = st.number_input("🔢 Quantidade", min_value=1, value=1, key="qtd_item")
        
        # Botão para adicionar item ao pedido
        if st.button("➕ Adicionar Item ao Pedido", type="secondary") and produto_selecionado and cliente_selecionado:
            produto_nome = produto_selecionado.split(' - ')[0]
            produto_tamanho = produto_selecionado.split('Tamanho: ')[1].split(' - ')[0]
            produto_cor = produto_selecionado.split('Cor: ')[1].split(' - ')[0]
            produto_preco = float(produto_selecionado.split('R$')[1].split(' - ')[0])
            produto_estoque = int(produto_selecionado.split('Estoque: ')[1])
            
            # Verificar se já existe o mesmo item no pedido
            item_existente = next((item for item in st.session_state.itens_pedido 
                                 if item['produto'] == produto_nome and item['tamanho'] == produto_tamanho), None)
            
            if item_existente:
                # Atualizar quantidade do item existente
                nova_quantidade_total = item_existente['quantidade'] + quantidade_item
                if nova_quantidade_total <= produto_estoque:
                    item_existente['quantidade'] = nova_quantidade_total
                    item_existente['subtotal'] = nova_quantidade_total * produto_preco
                    st.success(f"✅ Quantidade atualizada: {produto_nome} - Total: {nova_quantidade_total}")
                else:
                    st.error(f"❌ Estoque insuficiente! Disponível: {produto_estoque}")
            else:
                # Adicionar novo item
                if quantidade_item <= produto_estoque:
                    novo_item = {
                        'produto': produto_nome,
                        'tamanho': produto_tamanho,
                        'cor': produto_cor,
                        'quantidade': quantidade_item,
                        'preco_unitario': produto_preco,
                        'subtotal': quantidade_item * produto_preco
                    }
                    st.session_state.itens_pedido.append(novo_item)
                    st.success("✅ Item adicionado ao pedido!")
                else:
                    st.error(f"❌ Estoque insuficiente! Disponível: {produto_estoque}")
        
        # Exibir itens do pedido atual
        st.subheader("📋 Itens no Pedido")
        if st.session_state.itens_pedido:
            df_itens = pd.DataFrame(st.session_state.itens_pedido)
            st.dataframe(df_itens, use_container_width=True)
            
            # Calcular totais
            total_itens = len(st.session_state.itens_pedido)
            total_quantidade = sum(item['quantidade'] for item in st.session_state.itens_pedido)
            total_valor = sum(item['subtotal'] for item in st.session_state.itens_pedido)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🛒 Itens Diferentes", total_itens)
            col2.metric("📦 Total de Peças", total_quantidade)
            col3.metric("💰 Valor Total", f"R$ {total_valor:.2f}")
            
            # Botão para limpar pedido
            if st.button("🗑️ Limpar Todos os Itens", type="secondary"):
                st.session_state.itens_pedido = []
                st.rerun()
        else:
            st.info("🛒 Nenhum item adicionado ao pedido")
        
        # Dados finais do pedido
        st.subheader("📋 Finalizar Pedido")
        data_entrega = st.date_input("📅 Data de Entrega Prevista")
        observacoes = st.text_area("📝 Observações", placeholder="Cor específica, detalhes, etc...")
        
        # Botão final para criar pedido
        if st.button("✅ Finalizar Pedido", type="primary") and cliente_selecionado and st.session_state.itens_pedido:
            # Criar pedido principal
            novo_pedido = {
                'id': len(st.session_state.pedidos) + 1,
                'cliente': cliente_selecionado.split(' - ')[0],
                'escola': cliente_selecionado.split(' - ')[1],
                'itens': st.session_state.itens_pedido.copy(),  # Lista de itens
                'quantidade_total': sum(item['quantidade'] for item in st.session_state.itens_pedido),
                'valor_total': sum(item['subtotal'] for item in st.session_state.itens_pedido),
                'data_pedido': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'data_entrega_prevista': data_entrega.strftime("%d/%m/%Y"),
                'status': 'Pendente',
                'observacoes': observacoes
            }
            
            # Atualizar estoque para cada item
            for item in st.session_state.itens_pedido:
                for produto in st.session_state.produtos:
                    if (produto['nome'] == item['produto'] and 
                        produto.get('tamanho') == item['tamanho'] and
                        produto.get('cor') == item['cor']):
                        produto['estoque'] -= item['quantidade']
                        break
            
            st.session_state.pedidos.append(novo_pedido)
            st.session_state.itens_pedido = []  # Limpar itens do pedido
            salvar_dados()
            st.success("🎉 Pedido cadastrado com sucesso!")
            st.balloons()
        elif not st.session_state.itens_pedido and cliente_selecionado:
            st.error("❌ Adicione itens ao pedido antes de finalizar!")
    
    with tab2:
        st.header("📋 Lista de Pedidos")
        if st.session_state.pedidos:
            # Converter para DataFrame com tratamento de erros
            pedidos_data = []
            for pedido in st.session_state.pedidos:
                pedido_data = {
                    'id': pedido.get('id', 'N/A'),
                    'cliente': pedido.get('cliente', 'N/A'),
                    'escola': pedido.get('escola', 'N/A'),
                    'status': pedido.get('status', 'Pendente'),
                    'data_pedido': pedido.get('data_pedido', 'N/A'),
                    'data_entrega_prevista': pedido.get('data_entrega_prevista', 'N/A'),
                    'quantidade_total': pedido.get('quantidade_total', 0),
                    'valor_total': pedido.get('valor_total', 0)
                }
                
                # Tratar produtos antigos (sem lista de itens)
                if 'itens' in pedido:
                    # Novo formato com múltiplos itens
                    produtos_lista = [f"{item['produto']} (x{item['quantidade']})" for item in pedido['itens']]
                    pedido_data['produtos'] = ", ".join(produtos_lista)
                else:
                    # Formato antigo (produto único)
                    pedido_data['produtos'] = pedido.get('produto', 'N/A')
                    
                pedidos_data.append(pedido_data)
            
            df_pedidos = pd.DataFrame(pedidos_data)
            df_pedidos = df_pedidos.sort_values('id', ascending=False)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                status_filtro = st.multiselect("🔍 Filtrar por status:", 
                    options=df_pedidos['status'].unique(),
                    default=df_pedidos['status'].unique())
            with col2:
                escola_filtro = st.multiselect("🏫 Filtrar por escola:",
                    options=df_pedidos['escola'].unique(),
                    default=df_pedidos['escola'].unique())
            
            df_filtrado = df_pedidos[
                (df_pedidos['status'].isin(status_filtro)) & 
                (df_pedidos['escola'].isin(escola_filtro))
            ]
            
            st.dataframe(df_filtrado, use_container_width=True)
            st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_pedidos)} pedidos")
        else:
            st.info("📋 Nenhum pedido cadastrado")
    
    with tab3:
        st.header("🔄 Alterar Status do Pedido")
        if st.session_state.pedidos:
            # Criar lista de pedidos com tratamento seguro
            opcoes_pedidos = []
            for p in st.session_state.pedidos:
                cliente = p.get('cliente', 'N/A')
                produto = p.get('produto', 'Ver itens')  # Para pedidos antigos
                if 'itens' in p:
                    # Novo formato - mostrar primeiro item
                    if p['itens']:
                        produto = f"{p['itens'][0]['produto']} +{len(p['itens'])-1} itens" if len(p['itens']) > 1 else p['itens'][0]['produto']
                
                opcoes_pedidos.append(f"ID: {p.get('id', 'N/A')} - {cliente} - {produto} - Status: {p.get('status', 'Pendente')}")
            
            pedido_selecionado = st.selectbox("📦 Selecione o pedido", opcoes_pedidos)
            
            novo_status = st.selectbox("🎯 Novo Status", 
                ["Pendente", "Cortando", "Costurando", "Pronto", "Entregue", "Cancelado"])
            
            if st.button("🔄 Atualizar Status", type="primary"):
                pedido_id = int(pedido_selecionado.split(' - ')[0].replace('ID: ', ''))
                for pedido in st.session_state.pedidos:
                    if pedido.get('id') == pedido_id:
                        pedido['status'] = novo_status
                        break
                salvar_dados()
                st.success("✅ Status atualizado com sucesso!")
        else:
            st.info("📋 Nenhum pedido cadastrado")
    
    with tab4:
        st.header("✏️ Editar Pedido")
        if st.session_state.pedidos:
            # Criar lista de pedidos com tratamento seguro
            opcoes_editar = []
            for p in st.session_state.pedidos:
                cliente = p.get('cliente', 'N/A')
                produto = p.get('produto', 'Ver itens')
                if 'itens' in p and p['itens']:
                    produto = p['itens'][0]['produto']
                
                opcoes_editar.append(f"ID: {p.get('id', 'N/A')} - {cliente} - {produto}")
            
            pedido_editar = st.selectbox("📦 Selecione o pedido para editar", 
                opcoes_editar, key="editar_pedido")
            
            if pedido_editar:
                pedido_id = int(pedido_editar.split(' - ')[0].replace('ID: ', ''))
                pedido = next((p for p in st.session_state.pedidos if p.get('id') == pedido_id), None)
                
                if pedido:
                    st.warning("⚠️ Para pedidos com múltiplos itens, edite excluindo e criando novo pedido")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**👤 Cliente:** {pedido.get('cliente', 'N/A')}")
                        st.write(f"**🏫 Escola:** {pedido.get('escola', 'N/A')}")
                        
                        # Quantidade total (para pedidos antigos)
                        if 'quantidade' in pedido:
                            nova_quantidade = st.number_input("🔢 Nova Quantidade", 
                                min_value=1, value=pedido['quantidade'], key="qtd_edit")
                        else:
                            nova_quantidade = pedido.get('quantidade_total', 1)
                            st.write(f"**📦 Quantidade Total:** {nova_quantidade}")
                    
                    with col2:
                        # Data de entrega
                        if 'data_entrega_prevista' in pedido:
                            try:
                                data_antiga = datetime.strptime(pedido['data_entrega_prevista'], "%d/%m/%Y")
                            except:
                                data_antiga = datetime.now()
                        else:
                            data_antiga = datetime.now()
                        
                        nova_data = st.date_input("📅 Nova Data de Entrega", 
                            value=data_antiga, key="data_edit")
                        
                        novas_observacoes = st.text_area("📝 Novas Observações", 
                            value=pedido.get('observacoes', ''), key="obs_edit")
                    
                    if st.button("💾 Salvar Alterações", type="primary"):
                        # Atualizar dados básicos
                        pedido['data_entrega_prevista'] = nova_data.strftime("%d/%m/%Y")
                        pedido['observacoes'] = novas_observacoes
                        
                        # Para pedidos antigos com quantidade única
                        if 'quantidade' in pedido and pedido['quantidade'] != nova_quantidade:
                            # Reverter estoque antigo
                            produto_antigo = next((p for p in st.session_state.produtos 
                                if p['nome'] == pedido.get('produto') and p.get('tamanho') == pedido.get('tamanho')), None)
                            
                            if produto_antigo:
                                diferenca = nova_quantidade - pedido['quantidade']
                                produto_antigo['estoque'] -= diferenca
                                
                                if produto_antigo['estoque'] < 0:
                                    st.error("❌ Estoque insuficiente para esta quantidade!")
                                    produto_antigo['estoque'] += diferenca
                                else:
                                    pedido['quantidade'] = nova_quantidade
                                    salvar_dados()
                                    st.success("✅ Pedido atualizado com sucesso!")
                            else:
                                st.error("❌ Produto não encontrado no estoque")
                        else:
                            salvar_dados()
                            st.success("✅ Pedido atualizado com sucesso!")
        else:
            st.info("📋 Nenhum pedido cadastrado")

# CLIENTES - COM EDIÇÃO
elif menu == "👥 Clientes":
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "✏️ Editar Cliente"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        nome_cliente = st.text_input("👤 Nome do Cliente")
        escola_cliente = st.selectbox("🏫 Escola", st.session_state.escolas)
        telefone = st.text_input("📞 Telefone (WhatsApp)")
        email = st.text_input("📧 Email (opcional)")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome_cliente:
                novo_cliente = {
                    'id': len(st.session_state.clientes) + 1,
                    'nome': nome_cliente,
                    'escola': escola_cliente,
                    'telefone': telefone,
                    'email': email,
                    'data_cadastro': datetime.now().strftime("%d/%m/%Y")
                }
                st.session_state.clientes.append(novo_cliente)
                salvar_dados()
                st.success("✅ Cliente cadastrado com sucesso!")
            else:
                st.error("❌ Nome do cliente é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        if st.session_state.clientes:
            df_clientes = pd.DataFrame(st.session_state.clientes)
            
            # Estatísticas por escola
            st.subheader("📊 Distribuição por Escola")
            clientes_por_escola = df_clientes['escola'].value_counts()
            fig = px.pie(clientes_por_escola, values=clientes_por_escola.values, 
                        names=clientes_por_escola.index, title="Clientes por Escola")
            st.plotly_chart(fig)
            
            st.dataframe(df_clientes, use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")
    
    with tab3:
        st.header("✏️ Editar Cliente")
        if st.session_state.clientes:
            cliente_editar = st.selectbox("👥 Selecione o cliente para editar", 
                [f"{c['nome']} - {c['escola']} - Tel: {c.get('telefone', 'N/A')}" 
                 for c in st.session_state.clientes])
            
            if cliente_editar:
                cliente_nome = cliente_editar.split(' - ')[0]
                cliente = next((c for c in st.session_state.clientes if c['nome'] == cliente_nome), None)
                
                if cliente:
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_nome = st.text_input("👤 Nome", value=cliente['nome'])
                        nova_escola = st.selectbox("🏫 Escola", 
                            st.session_state.escolas, 
                            index=st.session_state.escolas.index(cliente['escola']))
                    with col2:
                        novo_telefone = st.text_input("📞 Telefone", value=cliente.get('telefone', ''))
                        novo_email = st.text_input("📧 Email", value=cliente.get('email', ''))
                    
                    if st.button("💾 Salvar Alterações", type="primary"):
                        cliente['nome'] = novo_nome
                        cliente['escola'] = nova_escola
                        cliente['telefone'] = novo_telefone
                        cliente['email'] = novo_email
                        salvar_dados()
                        st.success("✅ Cliente atualizado com sucesso!")
        else:
            st.info("👥 Nenhum cliente cadastrado")

# FARDAMENTOS - COM CAMPO ESCOLA
elif menu == "👕 Fardamentos":
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Fardamento", "📋 Listar Fardamentos", "✏️ Editar Fardamento"])
    
    with tab1:
        st.header("➕ Novo Fardamento")
        
        # ESCOLA - NOVO CAMPO ADICIONADO
        escola_fardamento = st.selectbox("🏫 Escola", st.session_state.escolas)
        
        # Categoria principal
        categoria_principal = st.selectbox("📦 Tipo de Fardamento", 
            ["Camisetas", "Calças/Shorts", "Agasalhos"])
        
        # Detalhes específicos por categoria
        if categoria_principal == "Camisetas":
            nome_produto = st.selectbox("👕 Modelo de Camiseta", tipos_camisetas)
            preco_sugerido = 29.90
        elif categoria_principal == "Calças/Shorts":
            nome_produto = st.selectbox("🩳 Modelo", tipos_calcas)
            preco_sugerido = 49.90
        else:  # Agasalhos
            nome_produto = st.selectbox("🧥 Modelo de Agasalho", tipos_agasalhos)
            preco_sugerido = 79.90
        
        # TAMANHOS COMPLETOS
        st.subheader("📏 Seleção de Tamanho")
        tamanho_selecionado = st.selectbox("Selecione o tamanho:", todos_tamanhos)
        
        # Campos comuns
        cor = st.text_input("🎨 Cor Principal", value="Branco")
        preco_produto = st.number_input("💰 Preço (R$)", min_value=0.0, step=0.01, value=preco_sugerido)
        estoque_inicial = st.number_input("📦 Estoque Inicial", min_value=0, value=10)
        descricao = st.text_area("📝 Descrição Adicional", placeholder="Gola V, malha fria, etc...")
        
        if st.button("✅ Cadastrar Fardamento", type="primary"):
            if nome_produto and tamanho_selecionado and escola_fardamento:
                novo_produto = {
                    'nome': nome_produto,
                    'escola': escola_fardamento,  # NOVO CAMPO ADICIONADO
                    'categoria': categoria_principal,
                    'tamanho': tamanho_selecionado,
                    'cor': cor,
                    'preco': preco_produto,
                    'estoque': estoque_inicial,
                    'descricao': descricao,
                    'data_cadastro': datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.produtos.append(novo_produto)
                salvar_dados()
                st.success("✅ Fardamento cadastrado com sucesso!")
                st.balloons()
            else:
                st.error("❌ Preencha todos os campos obrigatórios!")
    
    with tab2:
        st.header("📋 Fardamentos Cadastrados")
        if st.session_state.produtos:
            df_produtos = pd.DataFrame(st.session_state.produtos)
            
            # Filtros COM ESCOLA
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                escola_filtro = st.selectbox("🏫 Filtrar por escola:", 
                    ["Todas"] + list(df_produtos['escola'].unique()))
            with col2:
                cat_filtro = st.selectbox("🔍 Filtrar por categoria:", 
                    ["Todas"] + list(df_produtos['categoria'].unique()))
            with col3:
                tamanho_filtro = st.selectbox("📏 Filtrar por tamanho:",
                    ["Todos"] + list(df_produtos['tamanho'].unique()))
            with col4:
                cor_filtro = st.selectbox("🎨 Filtrar por cor:",
                    ["Todas"] + list(df_produtos['cor'].unique()))
            
            df_filtrado = df_produtos
            if escola_filtro != "Todas":
                df_filtrado = df_filtrado[df_filtrado['escola'] == escola_filtro]
            if cat_filtro != "Todas":
                df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_filtro]
            if tamanho_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['tamanho'] == tamanho_filtro]
            if cor_filtro != "Todas":
                df_filtrado = df_filtrado[df_filtrado['cor'] == cor_filtro]
            
            st.dataframe(df_filtrado, use_container_width=True)
            st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_produtos)} fardamentos")
        else:
            st.info("👕 Nenhum fardamento cadastrado")
    
    with tab3:
        st.header("✏️ Editar Fardamento")
        if st.session_state.produtos:
            produto_editar = st.selectbox("👕 Selecione o fardamento para editar", 
                [f"{p['nome']} - Escola: {p.get('escola', 'N/A')} - Tamanho: {p.get('tamanho', 'Único')} - Cor: {p.get('cor', 'N/A')} - Estoque: {p.get('estoque', 0)}" 
                 for p in st.session_state.produtos])
            
            if produto_editar:
                produto_nome = produto_editar.split(' - ')[0]
                produto_escola = produto_editar.split('Escola: ')[1].split(' - ')[0]
                produto_tamanho = produto_editar.split('Tamanho: ')[1].split(' - ')[0]
                produto = next((p for p in st.session_state.produtos 
                    if p['nome'] == produto_nome and p.get('escola') == produto_escola and p.get('tamanho') == produto_tamanho), None)
                
                if produto:
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_preco = st.number_input("💰 Novo Preço (R$)", 
                            value=produto['preco'], min_value=0.0, step=0.01)
                        novo_estoque = st.number_input("📦 Novo Estoque", 
                            value=produto['estoque'], min_value=0)
                        nova_escola = st.selectbox("🏫 Nova Escola", 
                            st.session_state.escolas, 
                            index=st.session_state.escolas.index(produto.get('escola', 'Municipal')))
                    with col2:
                        nova_cor = st.text_input("🎨 Nova Cor", value=produto.get('cor', ''))
                        nova_descricao = st.text_area("📝 Nova Descrição", 
                            value=produto.get('descricao', ''))
                    
                    if st.button("💾 Salvar Alterações", type="primary"):
                        produto['preco'] = novo_preco
                        produto['estoque'] = novo_estoque
                        produto['escola'] = nova_escola
                        produto['cor'] = nova_cor
                        produto['descricao'] = nova_descricao
                        salvar_dados()
                        st.success("✅ Fardamento atualizado com sucesso!")
        else:
            st.info("👕 Nenhum fardamento cadastrado")

# ESTOQUE
elif menu == "📦 Estoque":
    tab1, tab2, tab3 = st.tabs(["📊 Ajustar Estoque", "📋 Inventário Completo", "⚠️ Alertas"])
    
    with tab1:
        st.header("📊 Ajuste Rápido de Estoque")
        if st.session_state.produtos:
            produto_ajustar = st.selectbox("👕 Selecione o fardamento", 
                [f"{p['nome']} - Escola: {p.get('escola', 'N/A')} - Tamanho: {p.get('tamanho', 'Único')} - Cor: {p.get('cor', 'N/A')} - Estoque: {p.get('estoque', 0)}" 
                 for p in st.session_state.produtos])
            
            acao = st.radio("🎯 Ação:", ["➕ Adicionar Estoque", "➖ Remover Estoque", "🎯 Definir Estoque Exato"])
            quantidade = st.number_input("🔢 Quantidade", min_value=1, value=1)
            
            if st.button("🔄 Aplicar Ajuste", type="primary"):
                produto_nome = produto_ajustar.split(' - ')[0]
                produto_escola = produto_ajustar.split('Escola: ')[1].split(' - ')[0]
                produto_tamanho = produto_ajustar.split('Tamanho: ')[1].split(' - ')[0]
                produto = next((p for p in st.session_state.produtos 
                    if p['nome'] == produto_nome and p.get('escola') == produto_escola and p.get('tamanho') == produto_tamanho), None)
                
                if produto:
                    estoque_antigo = produto['estoque']
                    
                    if acao == "➕ Adicionar Estoque":
                        produto['estoque'] += quantidade
                        st.success(f"✅ +{quantidade} unidades adicionadas | Estoque: {estoque_antigo} → {produto['estoque']}")
                    elif acao == "➖ Remover Estoque":
                        if produto['estoque'] >= quantidade:
                            produto['estoque'] -= quantidade
                            st.success(f"✅ -{quantidade} unidades removidas | Estoque: {estoque_antigo} → {produto['estoque']}")
                        else:
                            st.error("❌ Estoque insuficiente!")
                    else:  # Definir Estoque Exato
                        produto['estoque'] = quantidade
                        st.success(f"✅ Estoque definido: {estoque_antigo} → {quantidade} unidades")
                    
                    salvar_dados()
        else:
            st.info("👕 Nenhum fardamento cadastrado")
    
    with tab2:
        st.header("📋 Inventário Completo")
        if st.session_state.produtos:
            df_estoque = pd.DataFrame(st.session_state.produtos)
            
            # Status de estoque
            def status_estoque(quantidade):
                if quantidade == 0:
                    return "🔴 Esgotado"
                elif quantidade < 3:
                    return "🟡 Crítico"
                elif quantidade < 10:
                    return "🟢 Normal"
                else:
                    return "🔵 Alto"
            
            df_estoque['Status'] = df_estoque['estoque'].apply(status_estoque)
            df_estoque = df_estoque.sort_values(['escola', 'categoria', 'tamanho', 'estoque'])
            
            st.dataframe(df_estoque, use_container_width=True)
            
            # Estatísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_itens = len(df_estoque)
                st.metric("📦 Total de Itens", total_itens)
            with col2:
                esgotados = len(df_estoque[df_estoque['estoque'] == 0])
                st.metric("🔴 Itens Esgotados", esgotados)
            with col3:
                estoque_baixo = len(df_estoque[df_estoque['estoque'] < 5])
                st.metric("🟡 Estoque Baixo", estoque_baixo)
            with col4:
                valor_total = (df_estoque['estoque'] * df_estoque['preco']).sum()
                st.metric("💰 Valor em Estoque", f"R$ {valor_total:.2f}")
            
        else:
            st.info("👕 Nenhum fardamento cadastrado")
    
    with tab3:
        st.header("⚠️ Alertas de Estoque")
        if st.session_state.produtos:
            # Produtos esgotados
            produtos_esgotados = [p for p in st.session_state.produtos if p.get('estoque', 0) == 0]
            produtos_baixo = [p for p in st.session_state.produtos if 0 < p.get('estoque', 0) < 5]
            
            if produtos_esgotados:
                st.error("🔴 PRODUTOS ESGOTADOS:")
                for produto in produtos_esgotados:
                    st.error(f"❌ {produto['nome']} - Escola: {produto.get('escola', 'N/A')} - Tamanho: {produto.get('tamanho', 'N/A')} - Cor: {produto.get('cor', 'N/A')}")
            
            if produtos_baixo:
                st.warning("🟡 ESTOQUE BAIXO (menos de 5 unidades):")
                for produto in produtos_baixo:
                    st.warning(f"⚠️ {produto['nome']} - Escola: {produto.get('escola', 'N/A')} - Tamanho: {produto.get('tamanho', 'N/A')} - Estoque: {produto.get('estoque', 0)}")
            
            if not produtos_esgotados and not produtos_baixo:
                st.success("✅ Todos os produtos com estoque adequado!")
        else:
            st.info("👕 Nenhum fardamento cadastrado")

# RELATÓRIOS - CORRIGIDO E COMPLETO
elif menu == "📈 Relatórios":
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Vendas", "📦 Estoque", "👥 Clientes", "👕 Produtos"])
    
    with tab1:
        st.header("💰 Relatório de Vendas")
        if st.session_state.pedidos:
            # Criar DataFrame seguro para relatórios
            vendas_data = []
            for pedido in st.session_state.pedidos:
                venda = {
                    'id': pedido.get('id', 'N/A'),
                    'cliente': pedido.get('cliente', 'N/A'),
                    'escola': pedido.get('escola', 'N/A'),
                    'status': pedido.get('status', 'Pendente'),
                    'data_pedido': pedido.get('data_pedido', 'N/A'),
                    'data_entrega_prevista': pedido.get('data_entrega_prevista', 'N/A'),
                    'quantidade_total': pedido.get('quantidade_total', 0),
                    'valor_total': pedido.get('valor_total', 0),
                    'observacoes': pedido.get('observacoes', '')
                }
                vendas_data.append(venda)
            
            df_vendas = pd.DataFrame(vendas_data)
            
            # Métricas de vendas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_vendas = len(df_vendas)
                st.metric("📦 Total de Pedidos", total_vendas)
            with col2:
                valor_total = df_vendas['valor_total'].sum()
                st.metric("💰 Valor Total", f"R$ {valor_total:.2f}")
            with col3:
                media_pedido = valor_total / total_vendas if total_vendas > 0 else 0
                st.metric("📊 Ticket Médio", f"R$ {media_pedido:.2f}")
            
            # Vendas por escola
            st.subheader("🏫 Vendas por Escola")
            if not df_vendas.empty:
                vendas_escola = df_vendas['escola'].value_counts()
                fig1 = px.bar(vendas_escola, title="Vendas por Escola")
                st.plotly_chart(fig1)
            
            # Vendas por status
            st.subheader("🎯 Status dos Pedidos")
            if not df_vendas.empty:
                vendas_status = df_vendas['status'].value_counts()
                fig2 = px.pie(vendas_status, values=vendas_status.values, 
                             names=vendas_status.index, title="Distribuição por Status")
                st.plotly_chart(fig2)
            
            # Tabela detalhada
            st.subheader("📋 Detalhes dos Pedidos")
            st.dataframe(df_vendas, use_container_width=True)
            
            # Exportar
            if st.button("📥 Exportar Relatório de Vendas", type="primary"):
                csv = df_vendas.to_csv(index=False)
                st.download_button(
                    label="⬇️ Baixar CSV",
                    data=csv,
                    file_name=f"relatorio_vendas_{datetime.now().strftime('%d%m%Y')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("📋 Nenhuma venda registrada")
    
    with tab2:
        st.header("📦 Relatório de Estoque")
        if st.session_state.produtos:
            df_estoque = pd.DataFrame(st.session_state.produtos)
            
            # Métricas de estoque
            col1, col2, col3 = st.columns(3)
            with col1:
                total_produtos = len(df_estoque)
                st.metric("👕 Total de Produtos", total_produtos)
            with col2:
                estoque_total = df_estoque['estoque'].sum()
                st.metric("📦 Estoque Total", estoque_total)
            with col3:
                valor_estoque = (df_estoque['estoque'] * df_estoque['preco']).sum()
                st.metric("💰 Valor em Estoque", f"R$ {valor_estoque:.2f}")
            
            # Estoque por categoria
            st.subheader("📊 Estoque por Categoria")
            if not df_estoque.empty:
                estoque_categoria = df_estoque.groupby('categoria')['estoque'].sum()
                fig3 = px.bar(estoque_categoria, title="Estoque por Categoria")
                st.plotly_chart(fig3)
            
            # Estoque por escola
            st.subheader("🏫 Estoque por Escola")
            if 'escola' in df_estoque.columns and not df_estoque.empty:
                estoque_escola = df_estoque.groupby('escola')['estoque'].sum()
                fig4 = px.pie(estoque_escola, values=estoque_escola.values, 
                             names=estoque_escola.index, title="Estoque por Escola")
                st.plotly_chart(fig4)
            
            # Tabela detalhada
            st.subheader("📋 Detalhes do Estoque")
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("👕 Nenhum produto cadastrado")
    
    with tab3:
        st.header("👥 Relatório de Clientes")
        if st.session_state.clientes:
            df_clientes = pd.DataFrame(st.session_state.clientes)
            
            # Métricas de clientes
            col1, col2 = st.columns(2)
            with col1:
                total_clientes = len(df_clientes)
                st.metric("👥 Total de Clientes", total_clientes)
            with col2:
                clientes_por_escola = df_clientes['escola'].nunique()
                st.metric("🏫 Escolas Atendidas", clientes_por_escola)
            
            # Clientes por escola
            st.subheader("📊 Clientes por Escola")
            if not df_clientes.empty:
                clientes_escola = df_clientes['escola'].value_counts()
                fig5 = px.bar(clientes_escola, title="Clientes por Escola")
                st.plotly_chart(fig5)
            
            # Tabela detalhada
            st.subheader("📋 Lista de Clientes")
            st.dataframe(df_clientes, use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")
    
    with tab4:
        st.header("👕 Relatório de Produtos")
        if st.session_state.produtos:
            df_produtos = pd.DataFrame(st.session_state.produtos)
            
            # Produtos mais vendidos (se tivermos dados de vendas)
            if st.session_state.pedidos:
                st.subheader("🔥 Produtos Mais Vendidos")
                # Extrair produtos dos itens dos pedidos
                todos_produtos = []
                for pedido in st.session_state.pedidos:
                    if 'itens' in pedido:
                        for item in pedido['itens']:
                            todos_produtos.append(item['produto'])
                    elif 'produto' in pedido:
                        todos_produtos.append(pedido['produto'])
                
                if todos_produtos:
                    produtos_vendidos = pd.Series(todos_produtos).value_counts().head(10)
                    fig6 = px.bar(produtos_vendidos, title="Top 10 Produtos Mais Vendidos")
                    st.plotly_chart(fig6)
                else:
                    st.info("📊 Nenhum dado de vendas disponível")
            
            # Tabela de produtos
            st.subheader("📋 Todos os Produtos")
            st.dataframe(df_produtos, use_container_width=True)
        else:
            st.info("👕 Nenhum produto cadastrado")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v6.1 - CORRIGIDO")

if st.sidebar.button("🔄 Recarregar Dados"):
    carregar_dados()
    verificar_e_corrigir_dados()
    st.rerun()

# Botão para resetar dados corrompidos
if st.sidebar.button("🗑️ Resetar Dados Corrompidos", type="secondary"):
    st.session_state.pedidos = []
    st.session_state.clientes = []
    st.session_state.produtos = []
    st.session_state.itens_pedido = []
    salvar_dados()
    st.success("✅ Dados resetados com sucesso!")
    st.rerun()

# Notificação de alertas
if 'alertas_mostrados' not in st.session_state:
    st.session_state.alertas_mostrados = True
    produtos_baixo_estoque = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    if produtos_baixo_estoque:
        st.toast("⚠️ Alertas de estoque baixo detectados! Verifique a seção de Estoque.")