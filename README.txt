BIPBIP - BOT DE MÚSICA PRO DISCORD
==================================
Toca o Spotify da tua conta (pelo app oficial do PC) e as rádios JB FM e Mix FM ao vivo.


COMANDOS
--------
/tocar <link ou busca>       Toca música, álbum, playlist ou artista
/tocar playlist funk         Playlists favoritas: funk, caxa, pagode, nightdrive
                             (aparecem como sugestão; a lista fica em PLAYLISTS no bot.py)
/fila <link ou busca>        Põe uma música na fila
/pular  /voltar              Próxima / anterior
/pausar  /continuar          Pausa / continua
/aleatorio <sim/não>         Modo aleatório
/tocando                     Painel com a música atual e os botões ⏮️ ⏯️ ⏭️ 🔀 ⏹️
/radio <JB FM / Mix FM>      Rádio ao vivo
/radio-link <url>            Qualquer outra rádio pelo link do stream
/parar                       Para tudo e sai do canal

Também dá pra controlar pelo app do Spotify no celular: é só escolher o
dispositivo do PC.


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
  - Bibliotecas Python           tudo do requirements.txt
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
Se o bot cair (ex.: sem internet), ele tenta de novo sozinho em 15s.

Pelo terminal também funciona:
  python bot.py


LINUX
-----
  sudo apt install ffmpeg python3-pip
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
