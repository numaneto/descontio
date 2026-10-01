# descont.io

Portal e API de ofertas e descontos. O projeto recebe entradas de fontes
heterogêneas, valida se elas representam ofertas comerciais e publica um
formato único:

- produto;
- imagem;
- preço final e preço original;
- cupom opcional;
- link público da oferta;
- categoria e produto canônico, quando classificados.

A fonte permanece privada para auditoria e deduplicação. O portal e a API não
expõem grupo, canal, texto bruto ou identificadores internos.

## Arquitetura

```text
Telegram hoje; e-mail, crawler e API futuramente
                         |
                         v
                 pré-filtro local
              URL + sinal comercial
                         |
                         v
                 Offer Formatter
          valida + extrai + normaliza via LLM
                         |
              +----------+----------+
              |                     |
         não é oferta             é oferta
              |                     |
     auditoria por 7 dias     SQLite + mídia
                                    |
                          +---------+---------+
                          |                   |
                     portal web          API pública
```

### Componentes

- **FastAPI + Jinja2**: portal HTML server-side e API JSON.
- **SQLModel + SQLite + Alembic**: persistência e migrações.
- **Telethon**: primeiro conector em produção, usando polling curto em vez de
  listener permanente.
- **Offer Formatter**: pré-filtro local e classificação/extração por endpoint
  OpenAI-compatible.
- **Abacus RouteLLM**: provedor atual em produção, com modelo fixo
  `Qwen/Qwen3.8-Flash-Next`.

O código do formatter não depende do Abacus: qualquer provedor compatível com
`POST /v1/chat/completions` pode ser usado por configuração.

## Offer Formatter

O pipeline em `app/parsers/pipeline.py` segue esta ordem:

1. Descarta sem custo entradas sem URL ou sinal comercial.
2. Envia os candidatos ao LLM.
3. O LLM devolve JSON com:
   - `is_offer`;
   - `rejection_reason`;
   - `product_name`;
   - `price`;
   - `price_original`;
   - `coupon_code`;
   - `offer_url`.
4. Entradas rejeitadas ficam em `rejected_inputs` por sete dias, sem imagem.
5. Ofertas aceitas são persistidas e publicadas.

Se o LLM estiver desabilitado ou indisponível, o sistema só publica quando o
parser local identificar nome, preço e link. Falhas do provedor não transformam
automaticamente entradas incompletas em ofertas.

## Privacidade das fontes

Os seguintes campos existem somente para operação interna:

- plataforma e identificador da fonte;
- nome interno da fonte;
- ID da mensagem original;
- texto bruto;
- links originais.

A API pública não devolve `source`, `source_label`, texto bruto ou IDs internos.
`source_links` preserva URLs recebidas para auditoria; `links` representa as
URLs públicas, permitindo aplicar regras de afiliado sem destruir o original.

## Uso e custo do LLM

Cada resposta do provedor gera um registro em `llm_usage_events`:

- modelo efetivamente usado;
- tokens de entrada e saída;
- total de tokens;
- custo estimado em dólares;
- sucesso ou falha;
- data e operação.

O painel protegido `/admin/llm-usage` apresenta o resumo por modelo e as
últimas chamadas. Configure os preços contratados:

```dotenv
LLM_INPUT_COST_PER_MILLION=0.15
LLM_OUTPUT_COST_PER_MILLION=0.47
```

Esses valores correspondem ao modelo Qwen usado atualmente via Abacus e devem
ser revisados ao trocar de modelo ou provedor.

## API pública

Documentação interativa:

- Swagger UI: `/docs`
- OpenAPI: `/openapi.json`

Endpoints:

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/offers` | Lista ofertas com busca, período e faixa de preço |
| `GET` | `/api/v1/offers/{id}` | Retorna uma oferta não arquivada |

Exemplo:

```bash
curl 'http://localhost:8000/api/v1/offers?q=notebook&days=3&price_max=3000&limit=20'
```

A API é aberta para leitura:

- anônimo: 30 requisições por hora/IP;
- com `X-API-Key`: limite configurado para a chave, padrão 1.000/h.

As chaves são administradas em `/admin/api-keys` e armazenadas somente como
hash SHA-256.

## Administração

As rotas `/admin/*` usam HTTP Basic e falham de forma segura quando
`ADMIN_USER`/`ADMIN_PASSWORD` não estão configurados.

| Rota | Uso |
|---|---|
| `/admin/channels` | Habilitar ou desabilitar fontes Telegram |
| `/admin/api-keys` | Criar e revogar chaves da API pública |
| `/admin/llm-usage` | Consultar tokens e custo estimado do formatter |

## Retenção

`scripts/retention_cleanup.py`:

- arquiva ofertas com mais de `RETENTION_DAYS`;
- remove a imagem física;
- preserva texto e metadados privados;
- remove auditorias rejeitadas após sete dias.

O padrão atual é:

```dotenv
RETENTION_DAYS=7
```

## Desenvolvimento local

```bash
cp .env.example .env
cp config/channels.example.yaml config/channels.yaml

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

Em outro terminal:

```bash
python scripts/poll_telegram.py
```

## Docker Compose

```bash
cp .env.example .env
cp config/channels.example.yaml config/channels.yaml
docker compose up -d --build
```

O Compose sobe apenas o serviço web. Polling, retenção e backups devem ser
agendados externamente:

```cron
*/5 * * * * cd /opt/descontio && docker compose run --rm web python scripts/poll_telegram.py
0 4 * * * cd /opt/descontio && docker compose run --rm web python scripts/retention_cleanup.py
```

Use `flock` no polling em produção para impedir execuções sobrepostas.

## Configurando o Telegram

1. Crie um app em <https://my.telegram.org/apps>.
2. Preencha `TELEGRAM_API_ID` e `TELEGRAM_API_HASH`.
3. Gere uma sessão:

   ```bash
   python scripts/telegram_login.py
   ```

4. Salve o resultado em `TELEGRAM_SESSION_STRING`.
5. Configure as fontes em `config/channels.yaml` ou faça o seed para a tabela
   `channels`.

A session string equivale a uma credencial de acesso à conta e nunca deve ser
commitada.

## Configurando o LLM

Exemplo com Abacus RouteLLM:

```dotenv
LLM_ENABLED=true
LLM_BASE_URL=https://routellm.abacus.ai/v1
LLM_API_KEY=
LLM_MODEL=Qwen/Qwen3.8-Flash-Next
LLM_INPUT_COST_PER_MILLION=0.15
LLM_OUTPUT_COST_PER_MILLION=0.47
```

Use uma API key dedicada por instalação/projeto. Nunca reutilize ou versione
credenciais no repositório.

## Testes

```bash
PYTHONPATH=. pytest -q
```

Os testes cobrem formatos reais do parser, busca textual e decisões básicas do
pré-filtro/formatter.

## Próximas etapas

- conectores para e-mail/newsletter, crawlers e APIs;
- transformação de links por programa de afiliados;
- obtenção de imagens limpas diretamente da página do produto;
- classificação automática em `Category`/`Product`;
- wizard de configuração inicial;
- rate limit compartilhado caso a aplicação passe a usar múltiplos workers.

## Segurança e responsabilidade

- não comite `.env`, session strings ou API keys;
- respeite termos das fontes, lojas e programas de afiliados;
- publique somente imagens e conteúdo cujo uso seja permitido;
- mantenha a URL original privada para auditoria de transformações de
  afiliado;
- não exponha dados de fontes privadas na API ou no HTML público.

## Licença

MIT — consulte [`LICENSE`](LICENSE).
