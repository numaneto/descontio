# descont.io

> Nome do repositório: `descontio` (`github.com/numaneto/descontio`), nome de
> marca/produto voltado pro usuário: **descont.io**.

Portal e API de ofertas e descontos. Entradas de fontes diferentes são
normalizadas para um formato único de oferta: produto, imagem, preço, link e
cupom opcional. A origem é mantida apenas internamente para auditoria,
deduplicação e operação; o portal público não identifica grupos ou canais.

O Telegram é a primeira fonte em produção. A arquitetura deve aceitar também
e-mail, newsletters, crawlers e APIs sem alterar o formato público da oferta.

## Como funciona

```text
Telegram / e-mail / crawler / API
               |
               v
       Offer Formatter
  valida + extrai + normaliza
               |
               v
        SQLite / mídia
          |         |
          v         v
       Portal     API pública
```

- **Captura Telegram**: `scripts/poll_telegram.py`, um *user-client*
  (biblioteca [Telethon](https://docs.telethon.dev/)), conectado com a sua
  própria conta — não um bot. Isso é necessário porque muitos grupos de
  ofertas não aceitam bots ou banem quem entra só com bot; um user-client lê
  passivamente os canais configurados. O polling roda em ciclos curtos via
  cron e persiste o último ID processado por canal.
- **Parser híbrido**: a maioria dos grupos de ofertas já usa um formato
  bem definido (`Valor:`, `Cupom:`, `Link:`, `De:`/`Por:`, hashtag
  `#Anuncio`) — `app/parsers/regex_parser.py` extrai isso com regex, sem
  custo de API. Só quando a extração falha (nenhum preço/produto
  reconhecido) o texto bruto é mandado pra um LLM (endpoint
  OpenAI-compatible configurável — ex: um Copilot Bridge/Ollama/OpenAI
  próprio) pedindo JSON estruturado. Ver `app/parsers/pipeline.py`.
- **Portal**: FastAPI + Jinja2 + HTMX (sem build JS), grid de cards com
  foto/produto/preço/cupom/link e filtros por data, preço e palavra-chave.

## Rodando localmente (dev)

```bash
cp .env.example .env      # preencha as variáveis (ver abaixo)
cp config/channels.example.yaml config/channels.yaml   # edite com seus grupos/canais
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

Em outro terminal, execute um ciclo do polling do Telegram (precisa de uma
sessão autorizada — ver "Configurando o Telegram" abaixo):

```bash
python scripts/poll_telegram.py
```

## Rodando em produção (Docker Compose)

```bash
cp .env.example .env
cp config/channels.example.yaml config/channels.yaml
docker compose up -d --build
```

O serviço `web` publica o portal e a API na porta `8000`. Em produção, o
polling do Telegram é disparado externamente por cron a cada cinco minutos.

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
   canais que você já participa/segue — o polling só processa o que estiver
   listado ali.

## Extensão do parser (LLM fallback)

`LLM_ENABLED=true` no `.env` habilita o fallback. `LLM_BASE_URL` +
`LLM_API_KEY` + `LLM_MODEL` apontam pra qualquer endpoint compatível com a
API de chat completions da OpenAI (self-hosted, Ollama com wrapper, ou a
própria OpenAI). O fallback só é chamado quando o regex não encontra preço
**e** nome de produto com confiança — a maioria dos posts nunca chega lá.

## Privacidade e responsabilidade

- Nenhuma credencial (session string do Telegram, chaves de API, segredo do
  provedor de LLM) deve ser commitada — use `.env` (git-ignorado) ou um
  gerenciador de segredos.
- Ao rodar publicamente, você é responsável por respeitar os termos de uso
  das fontes, programas de afiliados e direitos de imagem/conteúdo.

## Licença

MIT — ver `LICENSE`.
