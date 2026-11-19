# bipbip — bot de música para Discord

O bipbip toca no canal de voz do Discord:
- o **Spotify** da sua conta, pelo app oficial instalado no PC;
- as rádios **JB FM** e **Mix FM** ao vivo, ou qualquer outra rádio pelo link do stream;
- o áudio de vídeos do **YouTube**.

O bot roda em um PC com Windows, chamado aqui de **notebook host**. Os donos do bot também podem desligar esse PC por um comando no Discord.

## Comandos

Antes de usar um comando, entre em um canal de voz. Se você estiver em outro canal, o bot vai até você.

### Spotify
| Comando | O que faz |
|---|---|
| `/tocar <link ou busca>` | Toca uma música, álbum, playlist ou artista. Aceita link do Spotify, nome de música ou o nome de uma das playlists favoritas (ex.: `/tocar funk`) |
| `/playlist <nome>` | Toca uma das playlists favoritas, escolhida em uma lista |
| `/fila <link ou busca>` | Adiciona uma música à fila (somente músicas, não álbuns nem playlists) |
| `/pular` · `/voltar` | Vai para a próxima música ou volta para a anterior |
| `/pausar` · `/continuar` | Pausa ou continua de onde parou |
| `/aleatorio <sim/não>` | Liga ou desliga o modo aleatório |
| `/tocando` | Traz o painel da música atual para o fim do chat |

### Rádio
| Comando | O que faz |
|---|---|
| `/radio <JB FM / Mix FM>` | Toca a rádio ao vivo |
| `/radio-link <url>` | Toca qualquer outra rádio pelo link do stream |

### YouTube
| Comando | O que faz |
|---|---|
| `/youtube <link>` | Toca o áudio de um vídeo ou de uma live. Em links de playlist, toca o primeiro vídeo |

### Geral
| Comando | O que faz |
|---|---|
| `/parar` | Para tudo, sai do canal e envia o resumo da sessão |
| `/sair` | Para tudo e desliga o notebook host em 60 segundos (somente os donos) |
| `/ajuda` ou `/help` | Mostra a lista de comandos, visível só para quem pediu |

## Funcionalidades

### Painel "tocando agora"
Quando começa a tocar, o bot envia um painel no chat que se atualiza sozinho a cada 3 segundos.

- **Spotify:** mostra música, artista, álbum e capa, com os botões ⏮️ ⏯️ ⏭️ 🔀 ⏹️. O 🔀 fica verde quando o modo aleatório está ligado.
- **Rádio:** mostra o logo e a cor da estação, com botões para alternar entre JB FM e Mix FM (a que está no ar fica verde) e ⏹️ para parar. Na JB FM, o painel também mostra a música que está tocando; a Mix FM não divulga essa informação.

Existe apenas um painel por vez: quando um novo é enviado, o anterior é apagado. Os botões continuam funcionando mesmo depois que o bot é reiniciado. Se o bot não tiver a permissão **Inserir links** no canal, o painel aparece em texto simples.

### Resumo da sessão
Quando sai do canal, o bot envia no chat a duração da sessão e quanto tempo cada fonte tocou:
- **Spotify:** tempo de reprodução e número de músicas ouvidas (conta a partir de 30 segundos, o mesmo critério do Spotify);
- **Rádio:** tempo ouvindo e a rádio mais ouvida;
- **YouTube:** tempo ouvindo e número de vídeos.

Se nada tocou, o resumo não é enviado.

### Desligar o notebook host (`/sair`)
- Somente as pessoas listadas em `DONO_IDS` no `.env` podem usar o comando. Se `DONO_IDS` estiver vazio, apenas o dono do app no Discord Developer Portal tem permissão.
- O bot para tudo, agenda o desligamento do Windows para dali a 60 segundos e envia uma mensagem com o botão ❌ **Cancelar**, que também só funciona para os donos.
- Quando faltam 10 segundos, a mensagem muda para **"⚠️ Notebook host desligado com sucesso"** e o botão desaparece. Essa mensagem permanece no chat.

### Comportamentos automáticos
- **Abre o Spotify:** se o app estiver fechado, o `/tocar` abre o Spotify e espera até 30 segundos para ele ficar disponível.
- **Sai quando fica sozinho:** se todos saírem do canal de voz, o bot para, sai e envia o resumo.
- **Troca de fonte sem conflito:** ao passar do Spotify para rádio ou YouTube, o bot pausa o Spotify no PC.
- **Chat limpo:** as respostas aos comandos são apagadas depois de 5 segundos (ou 15, em caso de erro).
- **Uma cópia por vez:** se o bot já estiver rodando no PC, uma segunda cópia não é iniciada.
- **Registro:** tudo o que aparece na janela também é gravado em `bot.log`. Quando o arquivo passa de 2 MB, ele é renomeado para `bot.old.log`.

Também é possível controlar a música pelo app do Spotify no celular: basta escolher o PC como dispositivo.

## Instalação num PC novo (Windows 10/11)

### 1. Rodar o instalador
Dê dois cliques no **`instalar.bat`**. Ele instala sozinho, pelo `winget`:

| Programa | Para quê |
|---|---|
| **Visual C++ Redistributable** | Runtime da Microsoft; sem ele o ffmpeg não funciona |
| **Visual Studio Build Tools** (C++) | Compilador que alguns pacotes do pip precisam. É grande (alguns GB) |
| **Python 3.13** | Roda o bot |
| **ffmpeg** | Toca o áudio no Discord |
| **App do Spotify** | É ele que toca as músicas |
| **Deno** | O yt-dlp precisa dele para o `/youtube` |
| **Bibliotecas Python** | Tudo do `requirements.txt` (inclui o yt-dlp) |

Ele também cria o `.env` a partir do `.env.example`. Se der erro no meio, reinicie o PC e rode de novo: o que já está instalado é pulado.

### 2. Fazer na mão
1. Instale o **VB-Cable**, uma placa de som virtual: https://vb-audio.com/Cable/ e **reinicie o PC**.
2. Abra o **Spotify** e entre na sua conta.
3. Abra Configurações → Som → **Mixer de volume** e, no **Spotify**, defina o dispositivo de saída como **CABLE Input**. Assim, apenas o som do Spotify vai para o cabo virtual; o restante do PC continua normal.

### 3. Criar o bot no Discord e o app no Spotify (só na primeira vez)
Se já criou antes, só precisa dos tokens deles (passo 4).

**Bot no Discord**
1. Acesse https://discord.com/developers/applications, clique em **New Application**, abra a aba **Bot**, clique em **Reset Token** e copie o token.
2. Em **OAuth2 → URL Generator**, marque os scopes `bot` e `applications.commands` e as permissões `Connect`, `Speak`, `Send Messages` e `Embed Links`.
3. Abra a URL gerada e adicione o bot ao seu servidor.

**App no Spotify**
1. Acesse https://developer.spotify.com/dashboard e clique em **Create app**.
2. Em Redirect URI, use exatamente `http://127.0.0.1:8888/callback`.
3. Marque **Web API**, salve e copie o Client ID e o Client Secret.

### 4. Configuração e tokens (`.env`)
Toda a configuração fica em um único arquivo. Os tokens **não vão para o GitHub** (o `.gitignore` bloqueia), então em todo PC novo é preciso preencher o `.env` de novo. Se ele não existir, crie a partir do modelo (o `instalar.bat` já faz isso):
```bat
copy .env.example .env
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DISCORD_TOKEN` | Sim | Token do bot: Developer Portal → seu app → **Bot** → **Reset Token** |
| `SPOTIFY_CLIENT_ID` · `SPOTIFY_CLIENT_SECRET` | Sim | Spotify Dashboard → seu app → **Settings** (o secret fica em **View client secret**) |
| `SPOTIFY_REDIRECT_URI` | Sim | Mantenha `http://127.0.0.1:8888/callback` |
| `SPOTIFY_PC_DEVICE` | Não | Nome com que o PC aparece no Spotify. Se ficar vazio, usa o nome do computador |
| `DONO_IDS` | Não | Quem pode usar o `/sair` (veja abaixo) |
| `GUILD_ID` | Não | ID do seu servidor. Faz os comandos aparecerem na hora, em vez de levar até 1 hora |
| `CAPTURE_DEVICE` | Não | Altere apenas se o VB-Cable tiver outro nome |
| `RADIO_JB_URL` · `RADIO_MIX_URL` | Não | Preencha apenas se os links das rádios pararem de funcionar |

Exemplo:
```env
DISCORD_TOKEN=MTIzNDU2Nzg5...
SPOTIFY_CLIENT_ID=a1b2c3d4e5...
SPOTIFY_CLIENT_SECRET=f6g7h8i9j0...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```
Sem aspas e sem espaço em volta do `=` (a única exceção é o `DONO_IDS`, abaixo).

**Como preencher o `DONO_IDS`:** coloque uma pessoa por linha. O apelido serve apenas para você identificar cada ID.
```
DONO_IDS="
eu = 123456789012345678
amigo = 987654321098765432
"
```

Para descobrir o ID de alguém, ative no Discord a opção Configurações → **Avançado** → **Modo desenvolvedor**. Depois, clique com o botão direito no nome da pessoa e escolha **Copiar ID do usuário**. O ID é um número de 17 a 19 dígitos; o nome de usuário não funciona.

O bot só lê o `.env` ao iniciar. Depois de qualquer alteração, reinicie o bot.

O arquivo `.spotify-token` é criado sozinho: na primeira execução, o navegador abre para você autorizar o app do Spotify, e a autorização fica salva nele.

> **Se um token vazar** (ex.: commitou o `.env` sem querer): gere outro (**Reset Token** no Discord, **Rotate client secret** no Spotify) e atualize o `.env`.

### 5. Ligar o bot
Dê dois cliques no **`iniciar.bat`**. Ele:
- abre o app do Spotify;
- atualiza o yt-dlp, já que o YouTube muda com frequência e versões antigas deixam de funcionar;
- inicia o bot e, se ele cair (por falta de internet, por exemplo), tenta de novo após 15 segundos.

Para desligar o bot, feche a janela. Também é possível iniciar com `python bot.py`, mas sem esses recursos.

### Linux
```bash
sudo apt install ffmpeg python3-pip
curl -fsSL https://deno.land/install.sh | sh
pip install -r requirements.txt
```
Não tem VB-Cable: é preciso outro jeito de capturar o áudio do Spotify. O `/sair` também só funciona no Windows.

## Playlists favoritas
As opções do `/playlist` ficam em `PLAYLISTS`, no `bot.py` (máximo de 25). Para adicionar uma, inclua o nome e o link e reinicie o bot.

## Observações
- É necessário ter **Spotify Premium**: a API só permite controlar a reprodução em contas Premium.
- O app do Spotify precisa ficar aberto no PC. Enquanto o bot toca, o som do Spotify não sai nas caixas do PC, porque está indo para o cabo virtual.
- Uma conta toca **um stream por vez**: se você der play no celular, o bot para, e vice-versa.
- O bot só funciona enquanto o PC estiver ligado e com o bot em execução.
- Os links da JB FM e da Mix FM já estão no código. Se pararem de funcionar, coloque o novo link em `RADIO_JB_URL` ou `RADIO_MIX_URL` no `.env`.
- Versões anteriores usavam o librespot, mas o Spotify bloqueou a chave de áudio de várias contas: https://github.com/librespot-org/librespot/issues/1649

## O que nunca vai para o GitHub
Estes arquivos contêm seus tokens e senhas e já estão no `.gitignore`:
- `.env`
- `.spotify-token`
- `spotify-cache/`

Também ficam de fora os arquivos gerados pelo bot: `bot.log`, `bot.old.log`, `.yt-info.json` e `__pycache__/`. Só o `.env.example` (modelo sem dados reais) é publicado.
