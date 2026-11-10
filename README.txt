BIPBIP - BOT DE MÚSICA PRO DISCORD
==================================
Toca o Spotify da tua conta (pelo app oficial do PC), as rádios JB FM e Mix FM ao
vivo e o áudio de vídeos do YouTube.


COMANDOS
--------
/tocar <link ou busca>       Toca música, álbum, playlist ou artista
/playlist <nome>             Playlists favoritas: funk (ariel), caxa, pagode, nightdrive
                             (a lista fica em PLAYLISTS no bot.py; máx. 25. Depois de
                             mudar, reinicia o bot)
/fila <link ou busca>        Põe uma música na fila
/pular  /voltar              Próxima / anterior
/pausar  /continuar          Pausa / continua
/aleatorio <sim/não>         Modo aleatório
/tocando                     Painel com a música atual e os botões ⏮️ ⏯️ ⏭️ 🔀 ⏹️
/radio <JB FM / Mix FM>      Rádio ao vivo
/radio-link <url>            Qualquer outra rádio pelo link do stream
/youtube <link>              Toca o áudio de um vídeo do YouTube (link de playlist
                             toca o 1º vídeo)
/parar                       Para tudo e sai do canal
/ajuda  /help                Lista os comandos

Também dá pra controlar pelo app do Spotify no celular: é só escolher o
dispositivo do PC.

Resumo da sessão: no /parar (ou quando todo mundo sai do canal), o bot manda no
chat quanto tempo tocou de Spotify, rádio e YouTube, quantas músicas foram
ouvidas (30s ou mais) e a rádio favorita.


INSTALAÇÃO NUM PC NOVO (Windows 10/11)
======================================

1) Rodar o instalador
---------------------
Dá dois cliques no instalar.bat. Ele instala sozinho, pelo winget:
  - Visual C++ Redistributable   runtime da Microsoft; sem ele o ffmpeg não funciona
  - Visual Studio Build Tools    compilador C++ que alguns pacotes do pip precisam
                                 (é grande, alguns GB)
  - Python 3.13                  roda o bot
  - ffmpeg                       toca o áudio no Discord
  - App do Spotify               é ele que toca as músicas
  - Deno                         o yt-dlp precisa dele pro /youtube
  - Bibliotecas Python           tudo do requirements.txt (inclui o yt-dlp)
E cria o arquivo .env a partir do .env.example.

Se der erro no meio: reinicia o PC e roda de novo (o que já está instalado é pulado).


2) Fazer na mão
---------------
a. Instalar o VB-Cable (caixa de som virtual): https://vb-audio.com/Cable/
   e REINICIAR o PC.
b. Abrir o Spotify e fazer login.
c. Configurações > Som > Mixer de volume > Spotify:
   Dispositivo de saída = CABLE Input
   Assim só o Spotify vai pro cabo; o resto do PC continua normal.


3) Criar o bot no Discord e o app no Spotify (só na primeira vez)
----------------------------------------------------------------
Se já criou antes, só precisa dos tokens deles (passo 4).

Bot no Discord:
  1. https://discord.com/developers/applications > New Application > Bot
     > Reset Token e copia o token
  2. OAuth2 > URL Generator:
     scopes: bot + applications.commands
     permissões: Connect, Speak, Send Messages
  3. Abre a URL gerada e adiciona o bot no teu servidor

App no Spotify:
  1. https://developer.spotify.com/dashboard > Create app
  2. Redirect URI: http://127.0.0.1:8888/callback (tem que ser exatamente esse)
  3. Marca Web API e salva. Depois copia o Client ID e o Client Secret


4) Colocar os tokens no arquivo .env
------------------------------------
Os tokens NÃO vão pro GitHub (o .gitignore bloqueia). Então, em todo PC novo,
tem que preencher o .env de novo.

Se o .env não existir, copia o modelo:
  copy .env.example .env

Abre o .env e preenche:

  OBRIGATÓRIOS
  DISCORD_TOKEN          Discord Developer Portal > teu app > Bot > Reset Token
  SPOTIFY_CLIENT_ID      Spotify Dashboard > teu app > Settings
  SPOTIFY_CLIENT_SECRET  mesma tela, em "View client secret"
  SPOTIFY_REDIRECT_URI   deixa http://127.0.0.1:8888/callback (igual ao do dashboard)

  OPCIONAIS
  GUILD_ID               No Discord: botão direito no servidor > Copiar ID
                         (precisa do Modo Desenvolvedor ligado). Faz os comandos
                         aparecerem na hora.
  SPOTIFY_PC_DEVICE      Nome do PC como aparece no Spotify. Vazio = nome do computador
  CAPTURE_DEVICE         Só muda se o VB-Cable tiver outro nome
  RADIO_JB_URL           Só se o link da JB FM mudar
  RADIO_MIX_URL          Só se o link da Mix FM mudar

Exemplo:
  DISCORD_TOKEN=MTIzNDU2Nzg5...
  SPOTIFY_CLIENT_ID=a1b2c3d4e5...
  SPOTIFY_CLIENT_SECRET=f6g7h8i9j0...
  SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback

Sem aspas e sem espaço em volta do "=".

O arquivo .spotify-token é criado sozinho: na 1a vez que o bot roda, abre o
navegador pra autorizar o app do Spotify e o login fica salvo nele.

Se um token vazar (ex.: commitou o .env sem querer): gera outro (Reset Token no
Discord, Rotate client secret no Spotify) e atualiza o .env.


5) Ligar o bot
--------------
Dá dois cliques no iniciar.bat. Pra desligar, fecha a janela.
Ele também:
  - abre o app do Spotify (se já estiver aberto, só traz pra frente);
  - atualiza o yt-dlp antes de ligar (o YouTube muda direto e versão velha
    para de funcionar);
  - se o bot cair (ex.: sem internet), tenta de novo sozinho em 15s.

Tudo que aparece na janela também é salvo no bot.log (quando passa de 2 MB,
vira bot.old.log). Bom pra ver o que deu errado.

Pelo terminal também funciona:
  python bot.py


LINUX
-----
  sudo apt install ffmpeg python3-pip
  curl -fsSL https://deno.land/install.sh | sh
  pip install -r requirements.txt
Não tem VB-Cable: precisa de outro jeito de capturar o áudio do Spotify.


BOM SABER
---------
- Precisa de Spotify Premium (a API só deixa controlar a reprodução no Premium).
- O app do Spotify precisa ficar aberto no PC. Enquanto o bot toca, tu não ouve
  o Spotify nas caixas do PC (ele tá indo pro cabo).
- Uma conta toca um stream por vez: se tu der play no celular, o bot para
  (e vice-versa).
- O bot só toca enquanto o PC estiver ligado com ele rodando.
- Os links da JB FM e da Mix FM já vêm no código. Se um dia pararem de
  funcionar, cola o link novo em RADIO_JB_URL / RADIO_MIX_URL no .env.
- Antes era librespot, mas o Spotify bloqueou a chave de áudio pra várias contas:
  https://github.com/librespot-org/librespot/issues/1649
