"""
AGENTE @inabmente
Cria a imagem com IA, escreve a frase, monta a legenda e posta no Instagram.
Roda sozinho pelo GitHub Actions às 9h e às 18h (horário de Brasília).
NÃO coloque senhas neste arquivo: o token fica nos Secrets do GitHub.
"""

import io
import os
import random
import subprocess
import time
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

# ================= CONFIGURAÇÃO =================
TOKEN = os.environ["IG_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
API = "https://graph.instagram.com/v21.0"
ASSINATURA = "@inabmente"
LARGURA, ALTURA = 1080, 1350  # formato 4:5, aceito no feed
FUSO = ZoneInfo("America/Sao_Paulo")

CINEMA = ("cinematic photo, dark moody tones, dramatic lighting, high contrast, "
          "film grain, ultra detailed, no text, no letters, no watermark")
ANIME = ("dark anime illustration, dramatic lighting, intense atmosphere, "
         "highly detailed, no text, no letters, no watermark")
CARTOON = ("cute funny 3d cartoon illustration, colorful, soft lighting, "
           "no text, no letters, no watermark")

HASHTAGS_BASE = "#inabmente #motivação #mentalidade #reflexão #disciplina #foco"

# (tema das 9h, tema das 18h) de segunda a domingo
CALENDARIO = [
    ("resiliencia", "silencio"),   # segunda
    ("controle", "fe"),            # terça
    ("guerreiro", "visao"),        # quarta
    ("treino", "cidadania"),       # quinta
    ("ambicao", "humor"),          # sexta
    ("honra", "humor"),            # sábado
    ("fe", "reflexao"),            # domingo
]

CHAMADAS = {
    "padrao": [
        "Salva esse post para ler de novo quando precisar. 🔥",
        "Marca alguém que precisa ler isso hoje.",
        "Se essa frase é pra você, comenta 🔥",
        "Compartilha com quem está lutando em silêncio.",
        "Lê de novo. Devagar. Agora aplica.",
    ],
    "fe": [
        "Comenta 'Amém' se você crê. 🙏",
        "Compartilha com alguém que precisa de esperança hoje.",
        "Salva para lembrar nos dias difíceis. 🙏",
        "Marca alguém para quem você está orando.",
    ],
    "humor": [
        "Marca aquele amigo que é exatamente assim 😂",
        "Comenta 😂 se você também é assim.",
        "Ninguém: ... Eu: 😅",
        "Rir também é disciplina. Marca alguém 😂",
    ],
}

CATEGORIAS = {
    "resiliencia": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#resiliência #superação #nuncadesista",
        "cenas": [
            "a tired boxer training alone in an old gym at dawn, sweat dripping",
            "a boxer running up stone steps at sunrise over an old city, cold breath",
            "a bruised boxer getting up from the canvas in an empty arena, single spotlight",
        ],
        "frases": [
            "A vida vai te derrubar. O que define você é quantas vezes você levanta.",
            "Não é sobre o quanto você bate. É sobre o quanto você aguenta e continua.",
            "Cansado? Ótimo. Agora continue.",
            "Toda cicatriz é a prova de que você foi mais forte do que aquilo que tentou te destruir.",
            "Desistir é fácil. Por isso tanta gente faz.",
            "Quem luta pode perder. Quem não luta já perdeu.",
            "O round mais difícil é justamente o que te transforma em campeão.",
        ],
    },
    "silencio": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#trabalhosilencioso #mentalidadedelobo #constância",
        "cenas": [
            "a lone wolf standing in heavy rain at night, glowing eyes, intense stare",
            "a lion with a wet mane in the rain, intense fixed stare, black background",
            "a man training alone in a dark garage at 5am, rain on the window",
        ],
        "frases": [
            "Treine em silêncio. Deixe o resultado fazer o barulho.",
            "Enquanto eles dormem, você constrói.",
            "O lobo não perde o sono com a opinião das ovelhas.",
            "Menos conversa. Mais trabalho. O tempo vai falar por você.",
            "Ninguém vê as madrugadas. Todo mundo vê o resultado.",
            "Não anuncie seus planos. Mostre suas conquistas.",
            "O leão não precisa rugir para provar quem ele é.",
        ],
    },
    "controle": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#controleemocional #estratégia #inteligênciaemocional",
        "cenas": [
            "a man in a 1920s tweed suit and flat cap walking through a foggy industrial street, cold calculating look",
            "portrait of a calm man in a vintage three-piece suit and newsboy cap, fire and smoke behind him",
            "a man in a 1920s suit sitting alone at a dark bar table, thinking, dim warm light",
        ],
        "frases": [
            "Quem controla as emoções controla o jogo.",
            "Não reaja. Observe. Depois aja.",
            "A raiva é um cavalo selvagem. Ou você domina, ou ela te leva para o abismo.",
            "Silêncio também é resposta. E às vezes a mais inteligente.",
            "Ninguém tem poder sobre você, a não ser o que você entrega.",
            "Mantenha a calma na tempestade. É lá que se descobre quem manda.",
            "Pense como um estrategista, não como uma vítima.",
        ],
    },
    "fe": {
        "estilo": CINEMA, "chamada": "fe",
        "hashtags": "#fé #Deus #esperança #gratidão #versículododia",
        "cenas": [
            "a person kneeling in prayer on a mountain top at sunrise, rays of light breaking through dark clouds",
            "an old wooden cross on a hill under a stormy sky with a single beam of light",
            "a hand reaching toward a divine light in the darkness",
            "an old open bible on a wooden table lit by a single candle",
        ],
        "frases": [
            "Tudo posso naquele que me fortalece. — Filipenses 4:13",
            "Seja forte e corajoso. Não tenha medo, pois o Senhor está com você. — Josué 1:9",
            "O Senhor é o meu pastor; nada me faltará. — Salmo 23:1",
            "Vinde a mim, todos os que estais cansados e sobrecarregados, e eu vos aliviarei. — Mateus 11:28",
            "Deus não te trouxe até aqui para te abandonar agora.",
            "Quando você não consegue ver o caminho, confie em quem o criou.",
            "A fé não torna as coisas fáceis. Torna possíveis.",
            "Às vezes Deus acalma a tempestade. Às vezes Ele acalma você no meio dela.",
            "Ore como se tudo dependesse de Deus. Trabalhe como se tudo dependesse de você.",
            "Seu recomeço pode estar a uma oração de distância.",
        ],
    },
    "guerreiro": {
        "estilo": ANIME, "chamada": "padrao",
        "hashtags": "#estoicismo #guerreiro #dorvirouforça",
        "cenas": [
            "a lone samurai with a scarred face standing in the rain holding a katana",
            "a huge swordsman in dark armor with a giant sword on a battlefield at dusk, crows in the sky",
            "a wandering ronin walking alone through a misty bamboo forest",
        ],
        "frases": [
            "A dor não vai embora. Você é que fica forte o suficiente para carregá-la.",
            "Transforme sua dor em combustível.",
            "Um guerreiro não escolhe a batalha fácil. Ele se prepara para a difícil.",
            "Suas feridas não te definem. O que você faz com elas, sim.",
            "O caminho é solitário. Mas é seu.",
            "Aquele que vence a si mesmo é o mais forte dos guerreiros.",
            "Afie sua mente como uma espada: todos os dias.",
        ],
    },
    "visao": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#visão #propósito #longoprazo",
        "cenas": [
            "an eagle soaring above the clouds at sunset over mountain peaks",
            "extreme close-up of an eagle's eye, intense focus, dark background",
            "a man standing alone on a mountain summit above the clouds",
        ],
        "frases": [
            "Quem pensa pequeno nunca vê o horizonte.",
            "O topo é solitário porque poucos aceitam pagar o preço da subida.",
            "Não troque o que você mais quer pelo que você quer agora.",
            "Planeje em anos. Execute em dias.",
            "Enxergue longe. Os obstáculos ficam menores lá de cima.",
            "Seu futuro é construído pelo que você faz hoje, não amanhã.",
            "Águias voam alto porque não carregam o peso das opiniões alheias.",
        ],
    },
    "treino": {
        "estilo": ANIME, "chamada": "padrao",
        "hashtags": "#treino #superação #semlimites",
        "cenas": [
            "an anime martial artist training under a waterfall, glowing aura",
            "a muscular anime fighter doing push-ups in a destroyed arena, intense energy aura",
            "an anime warrior with spiky hair powering up, lightning all around him",
        ],
        "frases": [
            "Seu limite de hoje é o aquecimento de amanhã.",
            "Motivação te faz começar. Disciplina te faz continuar.",
            "Não pare quando estiver cansado. Pare quando terminar.",
            "Todo campeão já foi um iniciante que se recusou a desistir.",
            "Suor hoje, orgulho amanhã.",
            "O corpo alcança o que a mente acredita.",
            "Consistência vence talento quando o talento não é consistente.",
        ],
    },
    "cidadania": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#cidadania #consciência #pensamentocrítico #brasil",
        "cenas": [
            "a diverse crowd of people walking in a city square at dusk, seen from above",
            "a small green plant growing through cracked asphalt, dramatic light",
            "an old library with light rays through tall windows",
            "many hands joined together in the center, dramatic light",
        ],
        "frases": [
            "Democracia não termina no dia da eleição. Ela começa nele.",
            "Critique ideias, não pessoas.",
            "Um povo que não lê é fácil de enganar. De qualquer lado.",
            "Pesquise antes de compartilhar. Espalhar mentira também é uma forma de roubo.",
            "Não existe país melhor sem cidadão melhor.",
            "Seu voto é seu. Não entregue sua consciência a ninguém.",
            "Discordar com respeito é sinal de maturidade, não de fraqueza.",
        ],
    },
    "ambicao": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#ambição #empreendedorismo #mentalidadedetopo",
        "cenas": [
            "a man in a sharp suit looking at a city skyline at night from a skyscraper office",
            "a man working late at night on a high-tech armor in a futuristic workshop, sparks flying",
            "a luxury car on a rainy city street at night, neon reflections",
        ],
        "frases": [
            "Sonhe grande. Trabalhe maior ainda.",
            "Ninguém vai te dar nada. Vá lá e construa.",
            "Enquanto você reclama, alguém está trabalhando no seu sonho.",
            "Conforto é o lugar onde os sonhos vão morrer.",
            "Seja tão bom que não possam te ignorar.",
            "Trabalhe em silêncio até seus resultados falarem alto.",
            "Dinheiro sem caráter é só barulho. Construa os dois.",
        ],
    },
    "honra": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#honra #coragem #força",
        "cenas": [
            "a roman gladiator standing in the colosseum sand, sunlight through dust",
            "a spartan warrior with shield and spear in front of an army, red cape, dramatic sky",
            "an ancient warrior kneeling with his sword in the rain after battle",
        ],
        "frases": [
            "Força sem honra é só violência.",
            "O que você faz hoje ecoa por gerações.",
            "Mantenha sua palavra. É a única coisa que ninguém pode tirar de você.",
            "Um homem de honra não precisa de plateia.",
            "Fique de pé, mesmo que esteja sozinho.",
            "Coragem não é ausência de medo. É seguir em frente apesar dele.",
            "Lute pelo que é certo, não pelo que é fácil.",
        ],
    },
    "reflexao": {
        "estilo": CINEMA, "chamada": "padrao",
        "hashtags": "#reflexão #vida #propósito",
        "cenas": [
            "a man sitting alone on a bench at night under a streetlight in the rain",
            "an hourglass with falling sand on a dark background, dramatic light",
            "a lone figure walking on an empty road toward the horizon at dawn",
        ],
        "frases": [
            "Você não está atrasado. Está no seu tempo. Só não pare.",
            "Um dia você vai agradecer por não ter desistido.",
            "Cuide de quem cuida de você. O tempo não volta.",
            "Não espere a vida ficar fácil. Fique mais forte.",
            "O que você faz hoje te aproxima ou te afasta de quem você quer ser?",
            "Perdoar não muda o passado, mas liberta o seu futuro.",
            "A vida é curta demais para viver o sonho dos outros.",
        ],
    },
    "humor": {
        "estilo": CARTOON, "chamada": "humor",
        "hashtags": "#humor #bomhumor #vidareal #risos",
        "cenas": [
            "a funny cartoon sloth lying on a couch holding a tiny dumbbell",
            "a cartoon cat in gym clothes sleeping on a treadmill",
            "a cartoon dog in a business suit holding a giant coffee cup on monday morning",
            "a chubby cartoon panda trying to do yoga and falling over",
            "a cartoon turtle wearing a superhero cape, very slow but confident",
        ],
        "frases": [
            "Eu não desisto. Só faço uma pausa estratégica… de três dias.",
            "Segunda-feira: o dia oficial de começar a dieta desde 1500.",
            "Meu corpo é um templo. Meio abandonado, mas é um templo.",
            "Acordei cedo, fui produtivo, conquistei o mundo… no sonho. Agora vou levantar.",
            "Disciplina é fazer o que precisa, mesmo com o sofá chamando pelo seu nome.",
            "Não sou preguiçoso. Estou no modo economia de energia.",
            "Sexta chegou. Minha motivação também, mas foi direto pro fim de semana.",
            "Hoje o treino foi pesado: levantei do sofá sem apoiar as mãos.",
            "Paciência é uma virtude. Wi-Fi lento é um teste de fé.",
            "Plano para o fim de semana: descansar. Plano B: descansar com mais força.",
        ],
    },
}


# ================= FUNÇÕES =================
def item_da_vez(lista, nome, n):
    """Embaralha sempre do mesmo jeito e pega o item da vez (não repete até acabar)."""
    copia = list(lista)
    random.Random(nome).shuffle(copia)
    return copia[n % len(copia)]


def contador(categoria, dia, turno, agora):
    """Conta quantas vezes o tema já saiu, para ir trocando a frase."""
    vagas = [(d, t) for d in range(7) for t in range(2) if CALENDARIO[d][t] == categoria]
    semana = (agora.date().toordinal() - 1) // 7
    return semana * len(vagas) + vagas.index((dia, turno))


def carregar_fonte(tamanho):
    for caminho in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        if os.path.exists(caminho):
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def fundo_reserva():
    """Fundo escuro minimalista, usado se a IA de imagens falhar."""
    img = Image.new("RGB", (LARGURA, ALTURA))
    d = ImageDraw.Draw(img)
    for y in range(ALTURA):
        c = int(10 + 25 * y / ALTURA)
        d.line([(0, y), (LARGURA, y)], fill=(c, c, c + 5))
    return img


def gerar_fundo(prompt):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
           + f"?width={LARGURA}&height={ALTURA}&seed={random.randint(1, 999999)}&nologo=true")
    for tentativa in range(1, 4):
        try:
            print(f"🎨 Criando imagem (tentativa {tentativa})...")
            r = requests.get(url, timeout=180)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                return ImageOps.fit(img, (LARGURA, ALTURA))
            print("   Resposta inesperada:", r.status_code)
        except Exception as erro:
            print("   Falhou:", erro)
        time.sleep(15)
    print("⚠️ A IA de imagens não respondeu. Usando fundo escuro minimalista.")
    return fundo_reserva()


def quebrar_linhas(texto, fonte, largura_max, draw):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def montar_arte(img, frase):
    # Escurece a imagem e cria uma sombra embaixo para a frase aparecer bem
    img = ImageEnhance.Brightness(img).enhance(0.8).convert("RGBA")
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)
    inicio = int(ALTURA * 0.35)
    for y in range(inicio, ALTURA):
        alfa = int(220 * (y - inicio) / (ALTURA - inicio))
        ds.line([(0, y), (LARGURA, y)], fill=(0, 0, 0, alfa))
    img = Image.alpha_composite(img, sombra).convert("RGB")
    draw = ImageDraw.Draw(img)

    texto, _, referencia = frase.partition(" — ")
    margem, tamanho = 90, 80
    while True:
        fonte = carregar_fonte(tamanho)
        linhas = quebrar_linhas(texto, fonte, LARGURA - 2 * margem, draw)
        altura_linha = int(tamanho * 1.25)
        altura_total = altura_linha * len(linhas)
        if altura_total <= ALTURA * 0.40 or tamanho <= 36:
            break
        tamanho -= 4

    y = min(int(ALTURA * 0.64 - altura_total / 2), ALTURA - 220 - altura_total)
    for linha in linhas:
        largura = draw.textlength(linha, font=fonte)
        draw.text(((LARGURA - largura) / 2, y), linha, font=fonte,
                  fill="white", stroke_width=3, stroke_fill="black")
        y += altura_linha

    if referencia:
        fonte_ref = carregar_fonte(40)
        largura = draw.textlength(referencia, font=fonte_ref)
        draw.text(((LARGURA - largura) / 2, y + 15), referencia, font=fonte_ref,
                  fill=(230, 190, 90), stroke_width=2, stroke_fill="black")

    fonte_ass = carregar_fonte(32)
    largura = draw.textlength(ASSINATURA, font=fonte_ass)
    draw.text(((LARGURA - largura) / 2, ALTURA - 80), ASSINATURA,
              font=fonte_ass, fill=(200, 200, 200))
    return img


def montar_legenda(frase, categoria):
    cat = CATEGORIAS[categoria]
    chamada = random.choice(CHAMADAS[cat["chamada"]])
    return f"{frase}\n\n{chamada}\n\n{ASSINATURA}\n.\n{cat['hashtags']} {HASHTAGS_BASE}"


def enviar_imagem_para_github(caminho):
    for comando in (
        ["git", "config", "user.name", "agente-inabmente"],
        ["git", "config", "user.email", "agente-inabmente@users.noreply.github.com"],
        ["git", "add", caminho],
        ["git", "commit", "-m", f"Nova arte: {os.path.basename(caminho)}"],
        ["git", "push"],
    ):
        subprocess.run(comando, check=True)

    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{caminho}"
    print("⏳ Esperando o link da imagem ficar disponível...")
    for _ in range(15):
        try:
            if requests.head(url, timeout=20).status_code == 200:
                print("🔗 Link pronto:", url)
                return url
        except requests.RequestException:
            pass
        time.sleep(5)
    raise SystemExit("❌ O link da imagem não abriu. Confira se o repositório está PÚBLICO.")


def postar_instagram(url_imagem, legenda):
    print("📤 Enviando para o Instagram...")
    r = requests.post(f"{API}/{IG_USER_ID}/media",
                      data={"image_url": url_imagem, "caption": legenda, "access_token": TOKEN},
                      timeout=60).json()
    if "id" not in r:
        raise SystemExit(f"❌ Erro ao criar o post: {r}")
    id_container = r["id"]

    for _ in range(24):
        status = requests.get(f"{API}/{id_container}",
                              params={"fields": "status_code", "access_token": TOKEN},
                              timeout=30).json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise SystemExit("❌ O Instagram recusou a imagem.")
        time.sleep(5)

    r = requests.post(f"{API}/{IG_USER_ID}/media_publish",
                      data={"creation_id": id_container, "access_token": TOKEN},
                      timeout=60).json()
    if "id" not in r:
        raise SystemExit(f"❌ Erro ao publicar: {r}")
    print("✅ POST PUBLICADO NO INSTAGRAM! ID:", r["id"])


# ================= PROGRAMA PRINCIPAL =================
def converter_imagem_para_video(caminho_imagem, caminho_video, duracao=7):
    """Pega na arte gerada pelo teu script e transforma num Reel MP4 com efeito de zoom"""
    print(f"🎬 Converter imagem em Reel MP4: {caminho_imagem}")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", caminho_imagem,
        "-vf", "zoompan=z='min(zoom+0.0015,1.15)':s=1080x1920:d=210:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "-c:v", "libx264",
        "-t", str(duracao),
        "-pix_fmt", "yuv420p",
        "-r", "30",
        caminho_video
    ]
    subprocess.run(cmd, check=True)
    print("✅ Reel MP4 gerado com sucesso!")


def postar_reel_instagram(video_url, legenda):
    """Envia o vídeo MP4 para a API do Instagram como Reel"""
    print("🚀 A enviar Reel para o Instagram...")
    url_container = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": legenda,
        "access_token": TOKEN
    }
    res = requests.post(url_container, data=payload).json()
    creation_id = res.get("id")

    if not creation_id:
        print("❌ Erro ao criar container do Reel:", res)
        return

    print(f"📦 Container criado ID: {creation_id}. A aguardar processamento Meta...")

    url_status = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={TOKEN}"
    for _ in range(12):
        time.sleep(5)
        status_res = requests.get(url_status).json()
        status = status_res.get("status_code")
        print(f"⏳ Status do vídeo: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print("❌ Erro no processamento do vídeo:", status_res)
            return

    url_publish = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    pub_res = requests.post(url_publish, data={"creation_id": creation_id, "access_token": TOKEN}).json()
    print("🎉 Reel publicado no Instagram
def main():
    agora = datetime.now(FUSO)
    dia = agora.weekday()
    turno = 0 if agora.hour < 14 else 1
    categoria = CALENDARIO[dia][turno]
    cat = CATEGORIAS[categoria]

    n = contador(categoria, dia, turno, agora)
    frase = item_da_vez(cat["frases"], categoria + "-frases", n)
    cena = item_da_vez(cat["cenas"], categoria + "-cenas", n)

    print(f"📅 {agora:%d/%m/%Y %H:%M} | Tema: {categoria}")
    print(f"💬 Frase: {frase}")

    arte = montar_arte(gerar_fundo(f"{cena}, {cat['estilo']}"), frase)
    os.makedirs("posts", exist_ok=True)
    caminho = f"posts/{agora:%Y-%m-%d_%H%M%S}.jpg"
    arte.save(caminho, "JPEG", quality=92)

    url = enviar_imagem_para_github(caminho)
    postar_instagram(url, montar_legenda(frase, categoria))
def converter_imagem_para_video(caminho_imagem, caminho_video, duracao=7):
    """Pega na arte gerada pelo teu script e transforma num Reel MP4 com efeito de zoom"""
    print(f"🎬 Converter imagem em Reel MP4: {caminho_imagem}")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", caminho_imagem,
        "-vf", "zoompan=z='min(zoom+0.0015,1.15)':s=1080x1920:d=210:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "-c:v", "libx264",
        "-t", str(duracao),
        "-pix_fmt", "yuv420p",
        "-r", "30",
        caminho_video
    ]
    subprocess.run(cmd, check=True)
    print("✅ Reel MP4 gerado com sucesso!")


def postar_reel_instagram(video_url, legenda):
    """Envia o vídeo MP4 para a API do Instagram como Reel"""
    print("🚀 A enviar Reel para o Instagram...")
    url_container = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": legenda,
        "access_token": TOKEN
    }
    res = requests.post(url_container, data=payload).json()
    creation_id = res.get("id")

    if not creation_id:
        print("❌ Erro ao criar container do Reel:", res)
        return

    print(f"📦 Container criado ID: {creation_id}. A aguardar processamento Meta...")

    url_status = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={TOKEN}"
    for _ in range(12):
        time.sleep(5)
        status_res = requests.get(url_status).json()
        status = status_res.get("status_code")
        print(f"⏳ Status do vídeo: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print("❌ Erro no processamento do vídeo:", status_res)
            return

    url_publish = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    pub_res = requests.post(url_publish, data={"creation_id": creation_id, "access_token": TOKEN}).json()
    print("🎉 Reel publicado no Instagram
    [17:18, 24/09/2026] Roger Santos: caminho = f"posts/{agora:%Y-%m-%d_%H%M%S}.jpg"
arte.save(caminho, "JPEG", quality=92)

url = enviar_imagem_para_github(caminho)
postar_instagram(url, montar_legenda
[17:18, 24/09/2026] Roger Santos: caminho_jpg = f"posts/{agora:%Y-%m-%d_%H%M%S}.jpg"
caminho_mp4 = f"posts/{agora:%Y-%m-%d_%H%M%S}.mp4"

# 1. Guarda a imagem gerada pela tua função montar_arte()
arte.save(caminho_jpg, "JPEG", quality=92)

# 2. Converte a imagem no vídeo MP4 para Reel
converter_imagem_para_video(caminho_jpg, caminho_mp4, duracao=7)

# 3. Envia o vídeo MP4 para o GitHub
url_video = enviar_imagem_para_github(caminho_mp4)

# 4. Publica como Reel no Instagram
postar_reel_instagram(url_video, montar_legenda(frase, categoria))
[17:19, 24/09/2026] Roger Santos: # === ASSINATURA NO RODAPÉ DO REEL / IMAGEM ===
    largura, altura = arte.size
    draw = ImageDraw.Draw(arte)

    # Fonte para a assinatura no rodapé
    try:
        fonte_rodape = ImageFont.truetype("DejaVuSans-Bold.ttf", 38)
    except:
        fonte_rodape = ImageFont.load_default()

    # Desenha o nome @inabmente centralizado no fundo (rodapé)
    draw.text((largura // 2, altura - 180), "@inabmente", font=fonte_rodape, fill=(220, 220, 220), anchor="mm")
