# Sistema de Fardamentos Completo

Sistema de gerenciamento de pedidos de fardamentos com controle de estoque, clientes, produtos e relatórios.

## 🆕 Novas Funcionalidades na Versão 8.0

### ✅ Produtos Vinculados às Escolas
- Cada produto agora é cadastrado para uma escola específica
- Filtros por escola em todas as telas de produtos
- Relatórios mostram a escola de cada produto

### ✅ Clientes Simplificados
- Removido o vínculo de escolas dos clientes
- Clientes podem comprar produtos de qualquer escola
- Cadastro de clientes mais simples e rápido

### ✅ Melhorias na Interface
- Filtros por escola em produtos e estoque
- Visualização da escola em todos os lugares
- Interface mais limpa e intuitiva

## Funcionalidades Principais
- 📊 Dashboard com métricas em tempo real
- 📦 Gestão completa de pedidos
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
