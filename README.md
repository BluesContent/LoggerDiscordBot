# 🤖 Bot Multicorder — Discord + Google Drive

Bot que vigia pasta(s) **MIDIAS** no Google Drive. Quando, dentro da pasta da data de
hoje (ex: `20260714`), uma pasta de gravação recebe **todos os arquivos `Multicorder`
exigidos**, ele envia uma mensagem pré-definida (com @ marcações) num canal do Discord.

- Suporta **profundidade variável**: acha a gravação tanto direto (`VIDEO 01`) quanto
  aninhada (`VIRAL / CONVIDADO-A`).
- Ignora arquivos que não são gravação (ex: o sidecar `MultiCorder - ....xml`).
- Não repete: cada pasta é avisada **uma única vez**.
- **Multi-projeto**: um só bot atende vários projetos, cada um com sua pasta, seus
  índices exigidos, seu canal e sua mensagem — tudo em `projects.json`, sem mexer no código.

---

## 📂 Estrutura esperada no Drive

```
MIDIAS/                    ← você informa o ID dela (por projeto)
└── 20260714/              ← pasta da data (o bot calcula "hoje" sozinho)
    ├── VIDEO 01/          ← gravação direta
    │   ├── MultiCorder1 ... .mp4
    │   ├── MultiCorder2 ... .mp4
    │   └── ...            ← quando os índices exigidos chegam → mensagem ✅
    └── VIRAL/             ← categoria (ignorada; não tem MultiCorder direto)
        ├── CONVIDADO-A/   ← gravação aninhada
        └── CONVIDADO-B/
```

> **Índices exigidos:** neste projeto o conjunto completo é `1, 2, 3, 5, 6` (o **4 é
> pulado** por causa das entradas do vMix). Isso é configurável por projeto.

---

## ⚙️ Como configurar

A configuração é dividida em dois arquivos — **nenhum dos dois vai para o repositório**
(ambos estão no `.gitignore`, junto com a pasta `messages/`, pois carregam dados
específicos do seu servidor/projeto):

- **`.env`** → segredos e globais (token do bot, credencial Google, intervalo, fuso).
  Copie de `.env.example`.
- **`projects.json`** → a lista de projetos vigiados. Copie de `projects.example.json`:
  ```bash
  cp projects.example.json projects.json
  ```

### `.env` (copie de `.env.example`)
```env
DISCORD_TOKEN=...             # token do bot
GOOGLE_CREDENTIALS_FILE=credentials/service_account.json
POLL_INTERVAL_SECONDS=300     # checa a cada 5 min
TIMEZONE=America/Sao_Paulo
DATE_FORMAT=%Y%m%d
```

### `projects.json`
```json
{
  "projects": [
    {
      "name": "Projeto Principal",
      "midias_folder_id": "ID_DA_PASTA_MIDIAS",
      "required_indices": [1, 2, 3, 5, 6],
      "discord_channel_id": 123456789012345678,
      "message_file": "messages/projeto_principal.txt",
      "active_days": "ter",
      "active_start": "14:00",
      "active_end": "17:00"
    }
  ]
}
```

| Campo | O que é |
|---|---|
| `name` | Nome do projeto (só pra log/mensagem) |
| `midias_folder_id` | ID da pasta MIDIAS no Drive (parte da URL após `/folders/`) |
| `required_indices` | Quais números `Multicorder` fazem o "completo" |
| `discord_channel_id` | ID do canal onde a mensagem vai |
| `message_file` | Arquivo com o texto da mensagem |
| `active_days` | Dias ativos: `seg,ter,qua,qui,sex,sab,dom` (vazio = todos) |
| `active_start` / `active_end` | Faixa de horário `HH:MM` (vazio = sem limite) |

**Para adicionar outro projeto:** basta acrescentar outro objeto na lista `projects`
(com outra pasta, outros índices, outro canal e outra mensagem). Nenhuma mudança de código.

### Mensagem (`messages/*.txt`)
A pasta `messages/` é criada automaticamente (pelo painel ou na primeira execução) e
**não vai para o repositório** — o texto de cada projeto fica só na sua máquina. Exemplo
de conteúdo:

```
🎬 **Gravação finalizada!**

<@&ID_DO_CARGO>, a pasta **{path}** ({date}) já está com todos os arquivos no Drive.

📁 {link}
```

Placeholders disponíveis:
- `{path}` → caminho da pasta (ex: `VIRAL / CONVIDADO-A`)
- `{video}` → só o nome final da pasta (ex: `CONVIDADO-A`)
- `{date}` → data (ex: `20260714`)
- `{link}` → link direto pra pasta no Drive
- `{project}` → nome do projeto

Marcações (@): use os IDs — cargo `<@&ID_DO_CARGO>`, usuário `<@ID_DO_USUARIO>`
(Modo Desenvolvedor ligado → botão direito → Copiar ID).

---

## ✅ Instalação

```bash
git clone https://github.com/BluesContent/LoggerDiscordBot.git
cd LoggerDiscordBot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google Cloud (feito ✔️)
Conta de serviço criada, `credentials/service_account.json` no lugar e pasta MIDIAS
compartilhada com o e-mail do robô (permissão Leitor).

### Discord
1. <https://discord.com/developers/applications> → **New Application**.
2. **Bot** → **Reset Token** → copie pro `.env` (`DISCORD_TOKEN`).
3. **OAuth2 → URL Generator**: marque scope **`bot`** e permissões **Send Messages** +
   **View Channel** → abra a URL → adicione ao seu servidor.
4. No app do Discord: **Configurações → Avançado → Modo Desenvolvedor** ligado →
   botão direito no canal → **Copiar ID do canal** → cole em `discord_channel_id`.

---

## 🖥️ Painel web (jeito recomendado)

Você administra tudo por um painel no navegador — **sem editar arquivos**.

**Para abrir:** dê **dois cliques** no arquivo **`Abrir Painel.command`**.
(Na primeira vez ele instala as dependências sozinho; depois abre o navegador em
`http://127.0.0.1:5001`.)

No painel você pode:
- ➕ Criar/editar/excluir **projetos** (pasta do Drive, índices, canal, agenda)
- ✍️ Editar a **mensagem** e inserir **@menções** clicando nos cargos/@everyone
- 🔎 Ver o **status ao vivo** de cada pasta (completo / faltando / já avisado)
- 🧪 **Testar envio** no canal
- ▶️ **Ligar/Desligar** o monitoramento (enquanto o painel estiver aberto)
- 🗓️ Ver o **histórico** e liberar reenvio de uma pasta
- 🔑 Trocar o **token** e ajustes gerais na aba **Configurações**

> ⚠️ O monitoramento roda enquanto a janela do painel (Terminal) estiver aberta.
> Para rodar 24/7 sem depender disso, é a etapa da **Vercel**.

---

## 🔎 Testar sem enviar nada (diagnóstico via terminal)

```bash
source .venv/bin/activate
python diagnostico.py            # usa a data de hoje
python diagnostico.py 20260714   # força uma data
```
Mostra, por projeto, quais pastas estão completas e quais disparariam mensagem — **sem
tocar no Discord**. Ótimo pra validar antes de ligar o bot de verdade.

## ▶️ Rodar o bot

```bash
source .venv/bin/activate
python bot.py
```

---

## 🔒 Segurança
`DISCORD_TOKEN` e `service_account.json` são secretos e já estão no `.gitignore`.

## ☁️ Sobre a Vercel
A Vercel é serverless (não roda 24/7). A versão para lá será uma **Cron Function** que
faz uma verificação por vez e envia via API do Discord. As credenciais são as mesmas;
o código será adaptado quando chegarmos nessa etapa.
