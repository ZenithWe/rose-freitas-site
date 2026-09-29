# Rose Freitas • Site + Painel Administrativo

Projeto independente inspirado na arquitetura do **Camarote Resenha Morumbi**, adaptado para a operação da Rose Freitas.

## O que já existe

- Site público responsivo em preto e dourado
- Cursos e produtos
- Método YouTube 360°
- Coragem de Falar: O Despertar da sua Presença Autêntica
- VIP WhatsApp e VIP Telegram
- Cadastro de nome, celular e e-mail antes do fluxo VIP
- Solicitações VIP dentro do painel
- Filtros Todos / WhatsApp / Telegram
- Confirmar solicitação em verde e cancelar em vermelho
- Configuração de chave Pix e WhatsApp
- Área do cliente protegida por código temporário enviado por e-mail
- Materiais vinculados aos cursos
- Banners da página inicial
- Agenda
- Pedidos
- Clientes e liberação de acesso
- Financeiro simples (receita, despesas e saldo)
- Configuração de redes sociais, WhatsApp e textos principais
- Login administrativo
- Preparado para PostgreSQL e Render

## Rodar localmente

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py createsuperuser
python manage.py runserver
```

Site: http://127.0.0.1:8000/  
Painel: http://127.0.0.1:8000/painel/

## E-mail da área do cliente

Em desenvolvimento, se `EMAIL_HOST` não estiver configurado, o código temporário aparece no terminal do servidor.  
Em produção, configure SMTP usando as variáveis do `.env.example`.

## Deploy no Render

O repositório inclui `render.yaml`.

No Render, configure principalmente:

- `ALLOWED_HOSTS`: domínio do serviço, por exemplo `rose-freitas-site.onrender.com`
- `CSRF_TRUSTED_ORIGINS`: URL HTTPS completa
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_EMAIL`
- credenciais SMTP para os códigos da Área do Cliente

O banco PostgreSQL é definido pelo Blueprint do Render.

## Segurança

Nenhuma senha, chave de banco ou credencial SMTP deve ser salva no GitHub. Use variáveis de ambiente.

## Próximas integrações possíveis

Gateway de pagamento, webhook de confirmação automática, WhatsApp Cloud API, uploads privados de PDFs e integração com serviço de e-mail transacional.
