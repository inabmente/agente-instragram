import os, sys, json, time, requests
from datetime import datetime, timezone, timedelta

IG_ID = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_TOKEN"]
BASE  = "https://graph.instagram.com/v21.0"

slot = sys.argv[1] if len(sys.argv) > 1 else "manha"
hoje = datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d")
dia_semana = datetime.now(timezone(timedelta(hours=-3))).strftime("%A")

with open("posts.json", encoding="utf-8") as f:
    agenda = json.load(f)

post = agenda.get(hoje, {}).get(slot)
if not post:
    print(f"Nada agendado para {hoje} / {slot}. Encerrando.")
    raise SystemExit(0)

# Gera imagem com Pollinations (grátis, sem chave)
prompt_img = post.get("prompt", "dark cinematic portrait, dramatic lighting, moody, film grain")
seed = int(hoje.replace("-", "")) + (0 if slot == "manha" else 1)
img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt_img)}?width=1080&height=1350&seed={seed}&model=flux&nologo=true"

print(f"Imagem: {img_url[:80]}...")
print(f"Legenda: {post['caption'][:50]}...")

# 1) Cria container
r = requests.post(f"{BASE}/{IG_ID}/media", data={
    "image_url": img_url,
    "caption": post["caption"],
    "access_token": TOKEN
}, timeout=120).json()

if "id" not in r:
    raise SystemExit(f"ERRO no container: {r}")

print(f"Container criado: {r['id']}")
time.sleep(8)

# 2) Publica
p = requests.post(f"{BASE}/{IG_ID}/media_publish", data={
    "creation_id": r["id"],
    "access_token": TOKEN
}, timeout=60).json()

if "id" not in p:
    raise SystemExit(f"ERRO ao publicar: {p}")

print(f"✅ Publicado {hoje} / {slot} — ID {p['id']}")
