# Sistema de Fardamentos Completo

Sistema de gerenciamento de pedidos de fardamentos com controle de estoque, clientes, produtos e relatórios.

## 🆕 Correções na Versão 8.1

### ✅ Correção do Banco de Dados
- **Sistema de atualização automática** da estrutura do banco
- **Verificação de colunas** antes de executar queries
- **Compatibilidade** com bancos existentes e novos

### ✅ Ações Rápidas Funcionando
- **Navegação corrigida** entre páginas
- **Sistema de query params** para mudança de menu

### ✅ Status de Pedidos Aprimorado
- **5 status diferentes**: Pendente, Em produção, Pronto para entrega, Entregue, Cancelado
- **Controle completo** do fluxo do pedido
- **Data de entrega real** registrada automaticamente

## Como Funciona a Atualização do Banco
O sistema agora verifica automaticamente se as colunas necessárias existem e as cria se necessário:
1. `escola_id` na tabela `produtos`
2. `forma_pagamento` na tabela `pedidos`  
3. `data_entrega_real` na tabela `pedidos`

## Funcionalidades Principais
- 📊 Dashboard com métricas em tempo real
- 📦 Gestão completa de pedidos com status
- 👥 Cadastro simplificado de clientes
- 👕 Cadastro de produtos vinculados a escolas
- 📦 Controle de estoque automático
- 📈 Relatórios detalhados de vendas
- 🔐 Sistema de login com múltiplos usuários

## Login
- **Admin:** admin / Admin@2024!
- **Vendedor:** vendedor / Vendas@123

## Deploy no Render
1. Conecte seu repositório GitHub
2. Configure as variáveis de ambiente:
   - `DATABASE_URL`: URL do PostgreSQL
3. O deploy será automático

## Desenvolvimento Local
```bash
pip install -r requirements.txt
streamlit run app.py
