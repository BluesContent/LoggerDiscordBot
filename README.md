# 🤖 Bot Multicorder — Discord + Google Drive

Bot que vigia pasta(s) **MIDIAS** no Google Drive. Quando, dentro da pasta da data de
hoje (ex: `20260714`), uma pasta de gravação recebe **todos os arquivos `Multicorder`
exigidos**, ele envia uma mensagem pré-definida (com @ marcações) num canal do Discord.

- Suporta **profundidade variável**: acha a gravação tanto direto (`VIDEO 01`) quanto
  aninhada (`VIRAL / CONVIDADO-A`).
- Ignora arquivos que não são gravação (ex: o sidecar `MultiCorder - ....xml`).
- Não repete: cada pasta é avisada **uma única vez**.
- **Multi-projeto**: um só bot atende vários projetos, cada um com sua pasta, seus
  índices exigidos, seu canal e sua mensagem — tudo editável pelo **painel web**.
- Roda **100% local**, sem depender de nenhum serviço externo pago.

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

> **Índices exigidos:** por padrão o conjunto completo é `1, 2, 3, 4, 5, 6`, mas isso é
> configurável por projeto (ex: pulando o 4, se for o caso do seu setup de câmeras).

---

## ✅ Instalação

```bash
git clone https://github.com/BluesContent/LoggerDiscordBot.git
cd LoggerDiscordBot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google Cloud
1. Crie uma **Conta de Serviço** no [Google Cloud Console](https://console.cloud.google.com/)
   com a **Google Drive API** ativada.
2. Baixe a chave JSON e salve como `credentials/service_account.json`.
3. **Compartilhe a pasta MIDIAS** (no Drive) com o e-mail da conta de serviço
   (permissão de Leitor). O painel mostra esse e-mail com botão de copiar.

### Discord
1. <https://discord.com/developers/applications> → **New Application**.
2. **Bot** → **Reset Token** → copie (vai no `.env`).
3. **OAuth2 → URL Generator**: marque scope **`bot`** e permissões **Send Messages** +
   **View Channel** → abra a URL gerada → adicione ao seu servidor.
4. Ative o **Modo Desenvolvedor** no Discord (Configurações → Avançado) — útil se quiser
   pegar IDs manualmente (o painel já faz isso por você na maioria dos casos).

### `.env` (copie de `.env.example`)
```env
DISCORD_TOKEN=...
GOOGLE_CREDENTIALS_FILE=credentials/service_account.json
```
Apenas segredos ficam aqui. Todo o resto (projetos, mensagens, agenda, intervalo de
checagem) é configurado pelo painel e fica guardado em `data/` (criado automaticamente,
nunca vai para o repositório).

---

## 🖥️ Painel web (como usar no dia a dia)

Você administra tudo por um painel no navegador — **sem editar arquivos**.

**Para abrir:** dê **dois cliques** no arquivo **`Abrir Painel.command`**.
(Na primeira vez ele instala as dependências sozinho; depois abre o navegador em
`http://127.0.0.1:5001`.)

No painel você pode:
- ➕ Criar/editar/excluir **projetos** (pasta do Drive, índices, canal, agenda)
- ✍️ Editar a **mensagem** com um editor visual e inserir **@menções** clicando nos
  cargos/@everyone (sem precisar saber IDs)
- 🔎 Ver o **status ao vivo** de cada pasta (completo / faltando / já avisado)
- 🧪 **Testar envio** no canal
- ▶️ **Ligar/Desligar** o monitoramento
- 🗓️ Ver o **histórico** e liberar reenvio de uma pasta
- 🔑 Ajustar intervalo de checagem, fuso horário etc. na aba **Configurações**

> ⚠️ O monitoramento roda enquanto o painel (ou `bot.py`) estiver aberto no seu
> computador. Se o Mac desligar ou o programa fechar, o bot para.

---

## 🔎 Testar sem enviar nada (diagnóstico via terminal)

```bash
source .venv/bin/activate
python diagnostico.py            # usa a data de hoje
python diagnostico.py 20260714   # força uma data
```
Mostra, por projeto, quais pastas estão completas e quais disparariam mensagem — **sem
tocar no Discord**. Ótimo pra validar antes de ligar o bot de verdade.

## ▶️ Rodar o bot em loop (sem abrir o painel)

```bash
source .venv/bin/activate
python bot.py
```

---

## 🔒 Segurança
`DISCORD_TOKEN` e `credentials/service_account.json` são secretos e já estão no
`.gitignore`. A pasta `data/` (projetos, mensagens, histórico reais) também não vai
para o repositório.

## ☁️ Rodar na nuvem (pausado por enquanto)
O código já tem uma base pronta para rodar 24/7 na Vercel + Supabase (arquivos em
`api/`, `vercel.json`, `.github/workflows/check.yml`), mas essa etapa está **pausada**
— o bot está rodando local por enquanto. Quando quiser retomar, é só reativar o
agendamento no workflow do GitHub e configurar as variáveis de ambiente na Vercel.
