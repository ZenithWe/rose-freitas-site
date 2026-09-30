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

O `DATABASE_URL` é configurado no serviço existente; o Blueprint não cria um novo banco. A configuração PostgreSQL mantém o esquema `rose_app` e depois `public` no `search_path`.

## Compatibilidade e validação do backend

O redesign mantém Django, os modelos existentes, o login administrativo, os dados cadastrados e as variáveis de ambiente da implantação. Não adiciona migrações nem altera o esquema do banco. O app `core` continua usando o fluxo existente de `migrate --run-syncdb`. Os registros iniciais usam `get_or_create`: valores já editados pela administração não são sobrescritos.

O requisito Django foi atualizado de `5.2.6` para `5.2.17`, mantendo a série LTS 5.2 e incorporando as correções de segurança da série. Reinstale `requirements.txt` antes de executar as verificações.

As páginas públicas de cursos, VIP, afiliados e parcerias consultam os produtos ativos e os contatos existentes. `/robots.txt` e `/sitemap.xml` usam o domínio da requisição e não incluem páginas administrativas, recibos VIP ou a área do cliente no sitemap.

Os links `checkout_url` continuam apontando diretamente para o checkout cadastrado. A chave Pix e o WhatsApp continuam disponíveis no fluxo VIP. Este projeto não possui webhook de gateway, conciliação automática, gestão de comissões ou confirmação automática de Pix: a equipe confirma os pedidos no painel. Ao marcar um pedido como pago, a data de pagamento é preservada e o acesso existente do cliente ao produto é reativado, sem duplicar e-mails apenas por diferença entre maiúsculas e minúsculas. Cancelamento e reembolso continuam sem revogação automática de materiais; a administração deve decidir a liberação do acesso.

Excluir um produto com pedidos ou acessos agora desativa sua publicação e preserva o histórico, os materiais e os acessos dos clientes. Produtos sem esses vínculos podem ser excluídos. O recibo VIP usa a sessão do navegador que enviou a solicitação; um endereço sequencial não permite consultar a solicitação de outra pessoa.

O código da área do cliente continua com seis dígitos, hash e validade de dez minutos. Novos envios têm intervalo mínimo de sessenta segundos por e-mail e invalidam os códigos anteriores. A confirmação consome o código uma única vez, verifica se há acesso ativo e renova a identificação da sessão. Cinco erros invalidam o código. A contagem combina sessão e o cache padrão do Django, que é local ao processo: com vários processos, a contagem não é global e um cache compartilhado é necessário para um limite estrito entre todos os workers. A invalidação final e o intervalo de reenvio ficam no banco. A área do cliente e os recibos privados enviam `Cache-Control: no-store`.

Execute a suíte em ambiente local com SQLite e sem `DATABASE_URL` de produção:

```bash
python manage.py check
python manage.py test core
python manage.py collectstatic --noinput
```

Os testes usam um banco SQLite temporário, e-mail em memória e cache isolado. Cobrem publicação, links existentes, privacidade VIP, códigos, permissões, CSRF, cadastros, datas, finanças e preservação do histórico. Eles não comprovam entrega real de SMTP nem execução de pagamentos externos; esses pontos dependem das credenciais e dos serviços da implantação. Configure e verifique o envio real de e-mail antes de usar a área do cliente em produção: o backend de console é somente para desenvolvimento.

## Segurança

Nenhuma senha, chave de banco ou credencial SMTP deve ser salva no GitHub. Use variáveis de ambiente.

## Próximas integrações possíveis

Gateway de pagamento, webhook de confirmação automática, WhatsApp Cloud API, uploads privados de PDFs e integração com serviço de e-mail transacional.
