# descont.io

> Nome do repositório: `descontio` (`github.com/numaneto/descontio`), nome de
> marca/produto voltado pro usuário: **descont.io**.

Agregador pessoal de promoções: junta os posts de ofertas que já circulam em
grupos/canais do **Telegram** e **canais do WhatsApp** — texto, foto e link,
tal como o autor original postou — num único portal web pesquisável, com
filtro por data, loja e palavra-chave.

Não é um scraper de e-commerce nem um indexador de catálogo: a ideia é
simplesmente **compilar e organizar** o que os próprios grupos de ofertas já
publicam, num lugar só, em vez de acompanhar 10 grupos separados.

## Como funciona

```
Telegram (grupos/canais)  ──┐
                             ├──> Parser híbrido ──> SQLite ──> Portal web (FastAPI + HTMX)
WhatsApp (canais)         ──┘      (regex + LLM
                                     fallback)
```

- **Captura Telegram**: `workers/telegram_worker.py`, um *user-client*
  (biblioteca [Telethon](https://docs.telethon.dev/)), conectado com a sua
  própria conta — não um bot. Isso é necessário porque muitos grupos de
  ofertas não aceitam bots ou banem quem entra só com bot; um user-client lê
  passivamente qualquer grupo/canal que a conta já participa/segue.
- **Captura WhatsApp**: reaproveita uma instância existente do
  [Evolution API](https://github.com/EvolutionAPI/evolution-api) (não faz
  parte deste repo — é uma peça de infraestrutura separada). Configure um
  webhook do evento `messages.upsert` apontando pra
  `POST /webhook/whatsapp` deste serviço. Canais do WhatsApp chegam pelo
  mesmo evento, com `remoteJid` terminando em `@newsletter` (grupos normais
  terminam em `@g.us`) — o filtro de quais chats processar é feito via
  `config/channels.yaml`.
- **Parser híbrido**: a maioria dos grupos de ofertas já usa um formato
  bem definido (`Valor:`, `Cupom:`, `Link:`, `De:`/`Por:`, hashtag
  `#Anuncio`) — `app/parsers/regex_parser.py` extrai isso com regex, sem
  custo de API. Só quando a extração falha (nenhum preço/produto
  reconhecido) o texto bruto é mandado pra um LLM (endpoint
  OpenAI-compatible configurável — ex: um Copilot Bridge/Ollama/OpenAI
  próprio) pedindo JSON estruturado. Ver `app/parsers/pipeline.py`.
- **Portal**: FastAPI + Jinja2 + HTMX (sem build JS), grid de cards com
  foto/produto/preço/cupom/link, busca full-text (SQLite FTS5) e filtros
  por data/loja/grupo de origem.

## Rodando localmente (dev)

```bash
cp .env.example .env      # preencha as variáveis (ver abaixo)
cp config/channels.example.yaml config/channels.yaml   # edite com seus grupos/canais
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

Em outro terminal, o worker do Telegram (precisa de uma sessão autorizada —
ver "Configurando o Telegram" abaixo):

```bash
python workers/telegram_worker.py
```

## Rodando em produção (Docker Compose)

```bash
cp .env.example .env
cp config/channels.example.yaml config/channels.yaml
docker compose up -d --build
```

Serviços:
- `web`: portal (porta `8000`).
- `telegram-worker`: processo de longa duração conectado ao Telegram.

O webhook do WhatsApp é servido pelo próprio `web` em `/webhook/whatsapp` —
aponte o Evolution API pra ele (via reverse-proxy, se exposto fora da LAN).

## Configurando o Telegram (user-client)

1. Crie um app em https://my.telegram.org/apps (gera `api_id` e `api_hash` —
   **isso é uma credencial de API pessoal, nunca comite no repo**).
2. Preencha `TELEGRAM_API_ID`/`TELEGRAM_API_HASH` no `.env`.
3. Rode uma vez, interativamente, pra autorizar a sessão (pede o código
   enviado no próprio Telegram):
   ```bash
   python scripts/telegram_login.py
   ```
   Isso grava uma *session string* — **guarde-a como um segredo** (mesmo
   nível de sensibilidade de uma senha: dá acesso de leitura total à conta).
   Coloque em `TELEGRAM_SESSION_STRING` no `.env` (ou no gerenciador de
   segredos do seu deploy).
4. Edite `config/channels.yaml` com os `chat_id`/username dos grupos e
   canais que você já participa/segue — o worker só processa o que estiver
   listado ali.

## Configurando o WhatsApp (Evolution API)

Pressupõe que você já tem uma instância do Evolution API rodando e
conectada ao seu número (não é escopo deste repo). Configure o webhook da
instância pra enviar o evento `messages.upsert` pra:

```
POST https://<seu-deploy>/webhook/whatsapp
Header: X-Webhook-Secret: <WHATSAPP_WEBHOOK_SECRET do .env>
```

Siga/entre nos canais que você quer capturar com o número conectado, e
adicione o JID (`...@newsletter`) em `config/channels.yaml`.

## Extensão do parser (LLM fallback)

`LLM_ENABLED=true` no `.env` habilita o fallback. `LLM_BASE_URL` +
`LLM_API_KEY` + `LLM_MODEL` apontam pra qualquer endpoint compatível com a
API de chat completions da OpenAI (self-hosted, Ollama com wrapper, ou a
própria OpenAI). O fallback só é chamado quando o regex não encontra preço
**e** nome de produto com confiança — a maioria dos posts nunca chega lá.

## Privacidade e responsabilidade

- Este projeto **não redistribui** conteúdo de terceiros publicamente — é
  uma ferramenta de auto-hospedagem para uso pessoal, agregando grupos dos
  quais você já é membro/seguidor.
- Nenhuma credencial (session string do Telegram, chaves de API, segredo do
  webhook) deve ser commitada — use `.env` (git-ignorado) ou um gerenciador
  de segredos.
- Ao rodar publicamente, você é responsável por respeitar os termos de uso
  do Telegram/WhatsApp e direitos de imagem/conteúdo de terceiros no seu
  próprio deploy.

## Licença

MIT — ver `LICENSE`.
