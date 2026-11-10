"""
bipbip — bot de música: Spotify (tua conta, pelo app oficial do PC) + rádios do Rio.

Como funciona o Spotify:
  O app oficial do Spotify no PC toca numa "caixa de som virtual" (VB-Cable). O bot captura
  essa caixa com o ffmpeg e manda pro canal de voz. Os comandos (/tocar, /pular...) controlam o app do
  PC pela Web API. Também dá pra controlar pelo celular: é só escolher o dispositivo do PC.

  (Antes era librespot, mas o Spotify bloqueou a chave de áudio pra várias contas:
   https://github.com/librespot-org/librespot/issues/1649)

Feito pra UM servidor (uma conta do Spotify = um stream por vez).
"""
import asyncio
import os
import re
import shutil
import time
from pathlib import Path

import json
import subprocess
import sys

import aiohttp
import discord
import spotipy
import yt_dlp
from discord import app_commands
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

BASE = Path(__file__).resolve().parent
# Nome com que o app do Spotify do PC aparece na conta (normalmente o nome do computador)
DEVICE_NAME = os.getenv("SPOTIFY_PC_DEVICE") or os.getenv("COMPUTERNAME", "")
# Lado "saída" do cabo virtual, que o ffmpeg grava
CAPTURE_DEVICE = os.getenv("CAPTURE_DEVICE", "CABLE Output (VB-Audio Virtual Cable)")
GUILD_ID = os.getenv("GUILD_ID")  # opcional: comandos aparecem na hora nesse servidor

# ---------------------------------------------------------------- Spotify Web API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
    scope="user-read-playback-state user-modify-playback-state",
    cache_path=str(BASE / ".spotify-token"),
    open_browser=True,
))

SPOTIFY_LINK = re.compile(r"(track|album|playlist|artist)[/:]([A-Za-z0-9]{22})")


def find_device() -> str | None:
    for d in sp.devices().get("devices", []):
        if d["name"].lower() == DEVICE_NAME.lower():
            return d["id"]
    return None


async def wait_device(timeout: int) -> str:
    for _ in range(timeout):
        dev = await asyncio.to_thread(find_device)
        if dev:
            return dev
        await asyncio.sleep(1)
    raise RuntimeError(f"O app do Spotify do PC (**{DEVICE_NAME}**) não apareceu. "
                       "Ele tá aberto e logado?")


async def open_spotify_app() -> str:
    """Acha o app do PC; se não tiver aberto, abre e espera ele aparecer na conta."""
    dev = await asyncio.to_thread(find_device)
    if dev:
        return dev
    os.startfile("spotify:")  # abre o app (funciona na versão da Store e na do site)
    return await wait_device(30)


def capture_source() -> discord.FFmpegPCMAudio:
    """Grava o cabo virtual (onde o app do Spotify toca) e entrega pro Discord."""
    return discord.FFmpegPCMAudio(
        f"audio={CAPTURE_DEVICE}",
        before_options="-f dshow -audio_buffer_size 50",
        options="-vn",
    )


def to_uri(busca: str) -> tuple[str, str] | None:
    m = SPOTIFY_LINK.search(busca)
    return (m.group(1), f"spotify:{m.group(1)}:{m.group(2)}") if m else None


def search_track(q: str) -> tuple[str, str]:
    items = sp.search(q=q, type="track", limit=1)["tracks"]["items"]
    if not items:
        raise RuntimeError(f"Não achei nada pra **{q}**.")
    t = items[0]
    return t["uri"], f"{t['artists'][0]['name']} - {t['name']}"


def describe(kind: str, uri: str) -> str:
    _id = uri.split(":")[-1]
    try:
        if kind == "track":
            t = sp.track(_id)
            return f"{t['artists'][0]['name']} - {t['name']}"
        if kind == "album":
            a = sp.album(_id)
            return f"álbum {a['name']} ({a['artists'][0]['name']})"
        if kind == "artist":
            return f"artista {sp.artist(_id)['name']}"
    except Exception:
        pass
    return kind  # playlist de terceiros não expõe detalhes na API nova


def with_retry(fn, tries=5):
    """O dispositivo às vezes demora uns segundos pra aceitar comandos depois que aparece."""
    import time
    for i in range(tries):
        try:
            return fn()
        except spotipy.SpotifyException as e:
            if i == tries - 1 or e.http_status not in (404, 502, 503):
                raise
            time.sleep(1.5)


# ---------------------------------------------------------------- Rádios
RADIOS = {
    # chave: (nome exibido, termo de busca, texto que precisa estar no nome, variável p/ trocar URL)
    "jb": ("JB FM 99.9", "JB FM", "jb", "RADIO_JB_URL"),
    "mix": ("Mix FM Rio 102.1", "Mix", "mix", "RADIO_MIX_URL"),
}
# Links oficiais (StreamTheWorld). O "livestream-redirect" sempre manda pro servidor ativo.
RADIO_URLS = {
    "jb": "https://playerservices.streamtheworld.com/api/livestream-redirect/JBFMAAC.aac",
    "mix": "https://playerservices.streamtheworld.com/api/livestream-redirect/MIXRIOAAC.aac",
}
RADIO_BROWSER = [
    "https://de1.api.radio-browser.info",
    "https://de2.api.radio-browser.info",
    "https://fi1.api.radio-browser.info",
]
_radio_cache: dict[str, tuple[str, str]] = {}


async def resolve_radio(key: str) -> tuple[str, str]:
    """Link fixo; se não tiver, procura no radio-browser.info (diretório aberto de rádios)."""
    nome, termo, must, env = RADIOS[key]
    if os.getenv(env):
        return os.getenv(env), nome
    if key in RADIO_URLS:
        return RADIO_URLS[key], nome
    if key in _radio_cache:
        return _radio_cache[key]

    params = {"name": termo, "countrycode": "BR", "hidebroken": "true",
              "order": "votes", "reverse": "true", "limit": "100"}
    data = None
    async with aiohttp.ClientSession(headers={"User-Agent": "bipbip-discord-bot/1.0"}) as s:
        for srv in RADIO_BROWSER:
            try:
                async with s.get(f"{srv}/json/stations/search", params=params,
                                 timeout=aiohttp.ClientTimeout(total=8)) as r:
                    data = await r.json(content_type=None)
                break
            except Exception:
                continue
    if data is None:
        raise RuntimeError("radio-browser.info fora do ar. Coloca o link no .env.")

    nomes = [d for d in data if must in d["name"].lower()]
    rio = [d for d in nomes if "rio de janeiro" in (d.get("state") or "").lower()]
    escolhida = (rio or nomes or [None])[0]
    if not escolhida:
        raise RuntimeError(f"Não achei a {nome}. Coloca o link em {env} no .env.")
    res = (escolhida["url_resolved"] or escolhida["url"], escolhida["name"])
    _radio_cache[key] = res
    return res


FFMPEG_STREAM = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# ---------------------------------------------------------------- Discord
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
mode: str | None = None  # "spotify" | "radio" | None


async def ensure_voice(inter: discord.Interaction) -> discord.VoiceClient:
    global sessao
    if not inter.user.voice or not inter.user.voice.channel:
        raise RuntimeError("Entra num canal de voz primeiro.")
    vc = inter.guild.voice_client
    if sessao is None:
        sessao = Sessao(inter.channel)
    sessao.canal = inter.channel  # resumo vai pro canal do último comando
    if vc is None:
        return await inter.user.voice.channel.connect(self_deaf=True)
    if vc.channel != inter.user.voice.channel:
        await vc.move_to(inter.user.voice.channel)
    return vc


async def leave_spotify(vc: discord.VoiceClient | None):
    """Para a captura e pausa o app do PC (senão ele continua tocando no cabo à toa)."""
    global mode
    await remove_panel()
    if mode == "spotify":
        try:
            dev = await asyncio.to_thread(find_device)
            if dev:
                await asyncio.to_thread(sp.pause_playback, device_id=dev)
        except Exception:
            pass
    if vc and vc.is_playing():
        vc.stop()
    mode = None


async def spotify_ready(inter: discord.Interaction) -> str:
    """Garante bot no canal + app do Spotify aberto + captura rodando. Retorna device_id."""
    global mode
    vc = await ensure_voice(inter)
    dev = await open_spotify_app()
    if mode == "spotify" and vc.is_playing():
        return dev

    if vc.is_playing():
        vc.stop()  # tava tocando rádio
    vc.play(capture_source(), after=lambda e: e and print(f"[spotify] {e}"))
    mode = "spotify"
    await asyncio.to_thread(with_retry, lambda: sp.transfer_playback(dev, force_play=False))
    return dev


async def run(inter: discord.Interaction, coro):
    """Defer + tratamento de erro padrão. A resposta some sozinha pra não poluir o chat."""
    await inter.response.defer()
    ok = True
    try:
        msg = await coro
    except spotipy.SpotifyException as e:
        msg, ok = f"❌ Spotify: {e.msg}", False
    except Exception as e:
        msg, ok = f"❌ {e}", False
    if not ok:
        print(f"[/{inter.command.name if inter.command else '?'}] {msg}")
    try:
        m = await inter.followup.send(msg, wait=True)
        await m.delete(delay=5 if ok else 15)
    except discord.HTTPException:
        pass


# ---------------------------------------------------------------- Painel "tocando agora"
# Uma mensagem só, que se atualiza quando a música muda, com botões de controle.
panel: discord.Message | None = None
panel_state: tuple | None = None  # (id da faixa, tocando?) da última atualização


def build_panel(pb, can_embed: bool) -> dict:
    t = (pb or {}).get("item")
    shuffle = bool((pb or {}).get("shuffle_state"))
    view = Painel(shuffle)
    if not t or pb["device"]["name"].lower() != DEVICE_NAME.lower():
        return {"content": "🎵 Nada tocando no Spotify agora.", "embed": None, "view": view}
    quem = ", ".join(a["name"] for a in t.get("artists", [])) or t.get("show", {}).get("name", "")
    album = t.get("album", {})
    status = "▶️ Tocando" if pb["is_playing"] else "⏸️ Pausado"
    if shuffle:
        status += " · 🔀 Aleatório"
    if not can_embed:  # sem permissão "Inserir links": vai em texto mesmo
        return {"content": f"🎶 **{t['name']}** — {quem}\n💿 {album.get('name', '')} · {status}",
                "embed": None, "view": view}
    e = discord.Embed(title=t["name"], url=t.get("external_urls", {}).get("spotify"),
                      description=f"{quem}\n💿 {album.get('name', '')}", color=0x1DB954)
    if album.get("images"):
        e.set_thumbnail(url=album["images"][0]["url"])
    e.set_footer(text=status)
    return {"content": None, "embed": e, "view": view}


async def refresh_panel(force: bool = False, pb=None):
    global panel, panel_state
    msg = panel  # cópia local: o painel pode ser trocado/apagado durante os awaits
    if msg is None:
        return
    if pb is None:
        pb = await asyncio.to_thread(sp.current_playback)
    item = (pb or {}).get("item") or {}
    state = (item.get("id"), (pb or {}).get("is_playing"), (pb or {}).get("shuffle_state"))
    if state == panel_state and not force:
        return
    try:
        can_embed = msg.channel.permissions_for(msg.guild.me).embed_links
        novo = await msg.edit(**build_panel(pb, can_embed))
        if panel is msg:
            panel, panel_state = novo, state
    except discord.NotFound:  # alguém apagou o painel
        if panel is msg:
            panel = None


async def post_panel(channel):
    """Manda um painel novo no fim do chat (apaga o antigo)."""
    global panel, panel_state
    await remove_panel()
    try:
        panel = await channel.send("🎵 Carregando…", view=Painel())
    except discord.HTTPException as e:
        print(f"[painel] não consegui mandar no canal: {e}")
        return
    panel_state = None
    await asyncio.sleep(1.5)  # dá tempo do Spotify trocar de faixa
    await refresh_panel(force=True)


async def ensure_panel(channel):
    """Atualiza o painel que já existe; se não tiver nenhum, cria."""
    if panel is None:
        await post_panel(channel)
    else:
        await asyncio.sleep(1.5)
        await refresh_panel(force=True)


async def remove_panel():
    global panel, panel_state
    if panel is not None:
        try:
            await panel.delete()
        except discord.HTTPException:
            pass
    panel, panel_state = None, None


# ---------------------------------------------------------------- Resumo da sessão
MIN_OUVIDA = 30  # segundos pra contar como "música ouvida" (mesmo critério do Spotify)


class Sessao:
    """Do bot entrar no canal até o /parar. Mede o que realmente tocou."""

    def __init__(self, canal):
        self.inicio = time.monotonic()
        self.canal = canal
        self.spotify_seg = 0.0
        self.faixas: dict[str, float] = {}   # id da faixa -> segundos ouvidos
        self.radios: dict[str, float] = {}   # nome da rádio -> segundos ouvidos
        self.youtube_seg = 0.0
        self.videos: list[str] = []          # títulos dos vídeos tocados


sessao: Sessao | None = None
radio_atual: str | None = None


def fmt_tempo(seg: float) -> str:
    seg = int(seg)
    h, m = divmod(seg // 60, 60)
    if h:
        return f"{h}h {m:02d}min"
    if m:
        return f"{m}min"
    return f"{seg}s"


def contar(dt: float, pb):
    """Chamado a cada ~3s: soma o tempo no que tá tocando agora."""
    if sessao is None:
        return
    dt = min(dt, 10)  # se o loop engasgar, não conta um pulo enorme
    if mode == "spotify":
        item = (pb or {}).get("item")
        if item and pb.get("is_playing") and pb["device"]["name"].lower() == DEVICE_NAME.lower():
            sessao.spotify_seg += dt
            sessao.faixas[item["id"]] = sessao.faixas.get(item["id"], 0) + dt
    elif mode == "radio" and radio_atual and any(vc.is_playing() for vc in bot.voice_clients):
        sessao.radios[radio_atual] = sessao.radios.get(radio_atual, 0) + dt
    elif mode == "youtube" and any(vc.is_playing() for vc in bot.voice_clients):
        sessao.youtube_seg += dt


def resumo(s: Sessao) -> str | None:
    linhas = [f"📊 **Resumo da sessão** — durou {fmt_tempo(time.monotonic() - s.inicio)}"]
    if s.spotify_seg >= 1:
        musicas = sum(1 for seg in s.faixas.values() if seg >= MIN_OUVIDA)
        linhas.append(f"🎧 **Spotify:** {fmt_tempo(s.spotify_seg)} tocando · "
                      f"{musicas} música{'s' if musicas != 1 else ''} ouvida{'s' if musicas != 1 else ''}")
    if s.radios:
        total = sum(s.radios.values())
        fav, fav_seg = max(s.radios.items(), key=lambda kv: kv[1])
        linhas.append(f"📻 **Rádio:** {fmt_tempo(total)} ouvindo · favorita: **{fav}** ({fmt_tempo(fav_seg)})")
    if s.videos:
        n = len(s.videos)
        linhas.append(f"🎬 **YouTube:** {fmt_tempo(s.youtube_seg)} ouvindo · {n} vídeo{'s' if n != 1 else ''}")
    if len(linhas) == 1:
        return None  # entrou e saiu sem tocar nada
    return "\n".join(linhas)


async def fechar_sessao():
    global sessao
    s, sessao = sessao, None
    if s is None:
        return
    texto = resumo(s)
    if texto:
        try:
            await s.canal.send(texto)
        except discord.HTTPException as e:
            print(f"[resumo] não consegui mandar: {e}")


async def panel_loop():
    """A cada 3s: soma o tempo da sessão e atualiza o painel (uma consulta só ao Spotify)."""
    await bot.wait_until_ready()
    ultimo = time.monotonic()
    while not bot.is_closed():
        agora = time.monotonic()
        dt, ultimo = agora - ultimo, agora
        try:
            pb = None
            if mode == "spotify" or panel is not None:
                pb = await asyncio.to_thread(sp.current_playback)
            contar(dt, pb)
            if panel is not None:
                await refresh_panel(pb=pb)
        except Exception as e:
            print(f"[painel] {e}")
        await asyncio.sleep(3)


def _toggle(dev: str):
    pb = sp.current_playback()
    if pb and pb.get("is_playing"):
        sp.pause_playback(device_id=dev)
    else:
        sp.start_playback(device_id=dev)


def _toggle_shuffle(dev: str):
    pb = sp.current_playback()
    sp.shuffle(not (pb and pb.get("shuffle_state")), device_id=dev)


class Painel(discord.ui.View):
    """Botões do painel. timeout=None + custom_id = continuam funcionando depois de reiniciar."""

    def __init__(self, shuffle: bool = False):
        super().__init__(timeout=None)
        # 🔀 fica verde quando o aleatório tá ligado
        self.aleatorio.style = discord.ButtonStyle.success if shuffle else discord.ButtonStyle.secondary

    async def _acao(self, inter: discord.Interaction, action):
        await inter.response.defer()  # confirma o clique sem mandar mensagem
        try:
            dev = await asyncio.to_thread(find_device)  # olha o Spotify de verdade, não a memória
            if not dev:
                raise RuntimeError("O app do Spotify do PC não tá aberto.")
            await asyncio.to_thread(with_retry, lambda: action(dev))
        except Exception as e:
            await inter.followup.send(f"❌ {e}", ephemeral=True)
            return
        await asyncio.sleep(1)
        await refresh_panel(force=True)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="bipbip:voltar")
    async def voltar(self, inter, _):
        await self._acao(inter, lambda d: sp.previous_track(device_id=d))

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="bipbip:pausar")
    async def pausar(self, inter, _):
        await self._acao(inter, _toggle)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="bipbip:pular")
    async def pular(self, inter, _):
        await self._acao(inter, lambda d: sp.next_track(device_id=d))

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="bipbip:aleatorio")
    async def aleatorio(self, inter, _):
        await self._acao(inter, _toggle_shuffle)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="bipbip:parar")
    async def parar(self, inter, _):
        await inter.response.defer()
        await stop_all(inter.guild)


# ----------------------------------------------------- Spotify
# Playlists favoritas: viram as opções do /playlist (máx. 25). Pra adicionar outra, é só pôr aqui
# e reiniciar o bot.
PLAYLISTS = {
    "funk (ariel)": "https://open.spotify.com/playlist/32eoqHKRvx8gjHq8WiwikB",
    "caxa": "https://open.spotify.com/playlist/1g5Lm66Mf68wz8pZJSvnFB",
    "pagode": "https://open.spotify.com/playlist/4VWllQFROQ3n2QVEWxTCp0",
    "nightdrive": "https://open.spotify.com/playlist/5gg7nDWw3l8IZkvNAcZC7u",
}


def find_playlist(busca: str) -> tuple[str, str] | None:
    """Aceita 'playlist funk', 'funk', 'funk (ariel)', 'night drive'..."""
    q = re.sub(r"^play?lis?ty?\s+", "", busca.lower().strip())  # aceita "playlisty", "playist"...
    for nome, url in PLAYLISTS.items():
        curto = nome.split(" (")[0]
        if q.replace(" ", "") in (nome.replace(" ", ""), curto.replace(" ", "")):
            return nome, url
    return None


async def pc_device() -> str:
    """Device do app do PC, olhando o Spotify de verdade (não a memória do bot)."""
    dev = await asyncio.to_thread(find_device)
    if not dev:
        raise RuntimeError("O app do Spotify do PC não tá aberto. Usa /tocar.")
    return dev


@tree.command(name="tocar", description="Música, álbum, playlist ou artista (link ou busca)")
@app_commands.describe(busca="Link do Spotify ou nome da música")
async def sp_tocar(inter: discord.Interaction, busca: str):
    async def go():
        dev = await spotify_ready(inter)
        fav = find_playlist(busca)
        if fav:
            uri = to_uri(fav[1])[1]
            await asyncio.to_thread(with_retry, lambda: sp.start_playback(device_id=dev, context_uri=uri))
            return f"🎶 Tocando playlist **{fav[0]}**"
        link = to_uri(busca)
        if link is None:
            uri, nome = await asyncio.to_thread(search_track, busca)
            await asyncio.to_thread(with_retry, lambda: sp.start_playback(device_id=dev, uris=[uri]))
            return f"🎶 **{nome}**"
        kind, uri = link
        if kind == "track":
            await asyncio.to_thread(with_retry, lambda: sp.start_playback(device_id=dev, uris=[uri]))
        else:
            await asyncio.to_thread(with_retry, lambda: sp.start_playback(device_id=dev, context_uri=uri))
        return f"🎶 Tocando {await asyncio.to_thread(describe, kind, uri)}"

    async def go_painel():
        msg = await go()
        asyncio.create_task(post_panel(inter.channel))
        return msg
    await run(inter, go_painel())


@tree.command(name="playlist", description="Toca uma das playlists da galera")
@app_commands.describe(nome="Qual playlist")
@app_commands.choices(nome=[app_commands.Choice(name=n, value=n) for n in PLAYLISTS])
async def sp_playlist(inter: discord.Interaction, nome: app_commands.Choice[str]):
    async def go():
        dev = await spotify_ready(inter)
        uri = to_uri(PLAYLISTS[nome.value])[1]
        await asyncio.to_thread(with_retry, lambda: sp.start_playback(device_id=dev, context_uri=uri))
        asyncio.create_task(post_panel(inter.channel))
        return f"🎶 Tocando playlist **{nome.value}**"
    await run(inter, go())


@tree.command(name="fila", description="Põe uma música na fila (link ou busca)")
async def sp_fila(inter: discord.Interaction, busca: str):
    async def go():
        dev = await spotify_ready(inter)
        link = to_uri(busca)
        if link and link[0] != "track":
            raise RuntimeError("Fila só aceita música. Pra playlist/álbum usa /tocar.")
        uri, nome = (link[1], await asyncio.to_thread(describe, "track", link[1])) if link \
            else await asyncio.to_thread(search_track, busca)
        await asyncio.to_thread(with_retry, lambda: sp.add_to_queue(uri, device_id=dev))
        return f"➕ **{nome}** na fila"
    await run(inter, go())


def _spotify_cmd(name: str, desc: str, action, reply: str):
    @tree.command(name=name, description=desc)
    async def cmd(inter: discord.Interaction):
        async def go():
            dev = await pc_device()
            await asyncio.to_thread(with_retry, lambda: action(dev))
            asyncio.create_task(ensure_panel(inter.channel))
            return reply
        await run(inter, go())
    return cmd


_spotify_cmd("pular", "Próxima música", lambda d: sp.next_track(device_id=d), "⏭️ Pulou")
_spotify_cmd("voltar", "Música anterior", lambda d: sp.previous_track(device_id=d), "⏮️ Voltou")
_spotify_cmd("pausar", "Pausa", lambda d: sp.pause_playback(device_id=d), "⏸️ Pausado")
_spotify_cmd("continuar", "Continua de onde parou", lambda d: sp.start_playback(device_id=d), "▶️ Voltando")


@tree.command(name="aleatorio", description="Liga/desliga o modo aleatório")
async def sp_shuffle(inter: discord.Interaction, ligado: bool):
    async def go():
        dev = await pc_device()
        await asyncio.to_thread(with_retry, lambda: sp.shuffle(ligado, device_id=dev))
        asyncio.create_task(ensure_panel(inter.channel))
        return "🔀 Aleatório ligado" if ligado else "➡️ Aleatório desligado"
    await run(inter, go())


@tree.command(name="tocando", description="Mostra o painel com a música atual e os botões")
async def sp_tocando(inter: discord.Interaction):
    async def go():
        await pc_device()
        asyncio.create_task(post_panel(inter.channel))  # traz o painel pro fim do chat
        return "👇"
    await run(inter, go())


# ----------------------------------------------------- /radio
@tree.command(name="radio", description="Toca uma rádio ao vivo")
@app_commands.choices(estacao=[
    app_commands.Choice(name=v[0], value=k) for k, v in RADIOS.items()
])
async def radio(inter: discord.Interaction, estacao: app_commands.Choice[str]):
    async def go():
        global mode
        vc = await ensure_voice(inter)
        url, nome = await resolve_radio(estacao.value)
        await leave_spotify(vc)
        if vc.is_playing():
            vc.stop()
        vc.play(discord.FFmpegOpusAudio(url, **FFMPEG_STREAM),
                after=lambda e: e and print(f"[radio] {e}"))
        mode = "radio"
        global radio_atual
        radio_atual = nome
        return f"📻 No ar: **{nome}**"
    await run(inter, go())


@tree.command(name="radio-link", description="Toca qualquer rádio pelo link do stream")
async def radio_link(inter: discord.Interaction, url: str):
    async def go():
        global mode
        vc = await ensure_voice(inter)
        await leave_spotify(vc)
        if vc.is_playing():
            vc.stop()
        vc.play(discord.FFmpegOpusAudio(url, **FFMPEG_STREAM))
        mode = "radio"
        global radio_atual
        radio_atual = "rádio pelo link"
        return "📻 No ar"
    await run(inter, go())


# ----------------------------------------------------- /youtube
# O YouTube recusa (403) quando o ffmpeg baixa o link direto, principalmente em vídeo longo.
# Então o próprio yt-dlp baixa (em pedaços, do jeito que o YouTube aceita) e passa pro ffmpeg.
YTDL_OPTS = {"format": "bestaudio/best", "quiet": True, "no_warnings": True, "noplaylist": True}
YT_INFO = BASE / ".yt-info.json"
yt_proc: subprocess.Popen | None = None


def yt_info(url: str) -> dict:
    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.sanitize_info(ydl.extract_info(url, download=False))
    if info.get("entries"):  # link de playlist: pega o primeiro vídeo
        info = info["entries"][0]
    return info


def yt_stream(info: dict) -> subprocess.Popen:
    """Sobe o yt-dlp baixando o áudio pro stdout (reaproveita a busca já feita)."""
    stop_yt()
    YT_INFO.write_text(json.dumps(info), encoding="utf-8")
    global yt_proc
    yt_proc = subprocess.Popen(
        [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "-f", "bestaudio/best",
         "--load-info-json", str(YT_INFO), "-o", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return yt_proc


def stop_yt():
    global yt_proc
    if yt_proc is not None and yt_proc.poll() is None:
        yt_proc.kill()
        try:
            yt_proc.wait(3)
        except subprocess.TimeoutExpired:
            pass
    yt_proc = None


@tree.command(name="youtube", description="Toca o áudio de um vídeo do YouTube pelo link")
@app_commands.describe(link="Link do vídeo (youtube.com ou youtu.be)")
async def youtube(inter: discord.Interaction, link: str):
    async def go():
        global mode
        link_ = link.strip()
        if not re.match(r"https?://", link_):
            raise RuntimeError("Manda o link do vídeo (começando com https://).")
        vc = await ensure_voice(inter)
        try:
            info = await asyncio.to_thread(yt_info, link_)
        except yt_dlp.utils.DownloadError as e:
            print(f"[youtube] erro no link {link_}: {e}")
            raise RuntimeError(f"Não consegui abrir esse vídeo. {str(e).replace('ERROR: ', '')[:150]}")
        print(f"[youtube] tocando: {info.get('title')} ({link_})")
        await leave_spotify(vc)
        if vc.is_playing():
            vc.stop()
        proc = await asyncio.to_thread(yt_stream, info)

        def fim(e):
            print(f"[youtube] parou de tocar{f': {e}' if e else ''}")
            if yt_proc is proc:
                stop_yt()
        vc.play(discord.FFmpegOpusAudio(proc.stdout, pipe=True, options="-vn"), after=fim)
        mode = "youtube"
        titulo = info.get("title", "vídeo")
        if sessao:
            sessao.videos.append(titulo)
        dur = info.get("duration")
        dur_txt = f" `{int(dur) // 60}:{int(dur) % 60:02d}`" if dur else " 🔴 ao vivo" if info.get("is_live") else ""
        return f"🎬 Tocando **{titulo}**{dur_txt}"
    await run(inter, go())


# ----------------------------------------------------- geral
AJUDA = discord.Embed(title="🎵 bipbip — comandos", color=0x1DB954)
AJUDA.add_field(name="Spotify", inline=False, value=(
    "`/tocar <link ou busca>` — música, álbum, playlist ou artista\n"
    "`/fila <link ou busca>` — põe uma música na fila\n"
    "`/pular` · `/voltar` · `/pausar` · `/continuar`\n"
    "`/aleatorio <sim/não>` — modo aleatório\n"
    "`/tocando` — mostra o painel com a música atual"
))
AJUDA.add_field(name="Playlists", inline=False, value="\n".join(
    f"`/playlist {n}`" for n in PLAYLISTS
))
AJUDA.add_field(name="Rádio", inline=False, value=(
    "`/radio <JB FM / Mix FM>` — rádio ao vivo\n"
    "`/radio-link <url>` — qualquer rádio pelo link do stream"
))
AJUDA.add_field(name="YouTube", inline=False, value=(
    "`/youtube <link>` — toca o áudio de um vídeo"
))
AJUDA.add_field(name="Geral", inline=False, value=(
    "`/parar` — para tudo e sai do canal\n"
    "`/ajuda` — esta mensagem"
))
AJUDA.set_footer(text="Entra num canal de voz antes de chamar o bot. "
                      "Também dá pra controlar o Spotify pelo app, no dispositivo do PC.")


async def _ajuda(inter: discord.Interaction):
    await inter.response.send_message(embed=AJUDA, ephemeral=True)


tree.command(name="ajuda", description="Lista os comandos do bot")(_ajuda)
tree.command(name="help", description="Lista os comandos do bot")(_ajuda)

async def stop_all(guild: discord.Guild):
    global radio_atual
    vc = guild.voice_client
    await leave_spotify(vc)  # já pausa o app do PC e apaga o painel
    radio_atual = None
    if vc:
        vc.stop()
        await vc.disconnect()
    await fechar_sessao()  # manda o resumo no chat


@tree.command(name="parar", description="Para tudo e sai do canal")
async def parar(inter: discord.Interaction):
    async def go():
        await stop_all(inter.guild)
        return "👋 Falou, rapaziada"
    await run(inter, go())


@bot.event
async def on_voice_state_update(member, before, after):
    """Sai sozinho se ficar só no canal."""
    vc = member.guild.voice_client
    if vc and vc.channel and all(m.bot for m in vc.channel.members):
        await stop_all(member.guild)


async def setup_hook():
    bot.add_view(Painel())  # botões de painéis antigos continuam funcionando
    asyncio.create_task(panel_loop())


bot.setup_hook = setup_hook


@bot.event
async def on_ready():
    if GUILD_ID:
        g = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=g)
        await tree.sync(guild=g)  # aparecem na hora nesse servidor
        tree.clear_commands(guild=None)
        await tree.sync()  # apaga os globais antigos (senão aparece tudo duplicado)
    else:
        await tree.sync()
    print(f"✅ Online como {bot.user}")


def single_instance():
    """Trava numa porta local: se já tiver um bipbip rodando, este nem sobe.
    (Dois bots ao mesmo tempo brigam pelos cliques e apagam o painel um do outro.)"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 47391))
    except OSError:
        print("⚠️ Já tem um bipbip rodando neste PC. Fecha o outro antes.")
        raise SystemExit(3)
    return s  # precisa ficar vivo enquanto o bot roda


class _Tee:
    """Escreve na janela e no bot.log ao mesmo tempo."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass


def log_em_arquivo():
    import sys
    log = BASE / "bot.log"
    if log.exists() and log.stat().st_size > 2_000_000:  # não deixa crescer pra sempre
        log.replace(BASE / "bot.old.log")
    f = open(log, "a", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, f)
    sys.stderr = _Tee(sys.__stderr__, f)


if __name__ == "__main__":
    _lock = single_instance()
    log_em_arquivo()
    print(f"\n===== bipbip ligando ({time.strftime('%d/%m %H:%M:%S')}) =====")
    if not shutil.which("ffmpeg"):
        raise SystemExit("❌ 'ffmpeg' não encontrado no PATH. Veja o README.txt.")
    if not DEVICE_NAME:
        raise SystemExit("❌ Coloca SPOTIFY_PC_DEVICE no .env (nome do PC no Spotify).")
    print(f"Spotify conectado como: {sp.current_user()['display_name']}")  # 1ª vez abre o navegador
    bot.run(os.environ["DISCORD_TOKEN"])
