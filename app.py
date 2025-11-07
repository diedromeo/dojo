#!/usr/bin/env python3
"""
Samurai Scroll Portal — Render-Compatible CTF Version
----------------------------------------------------
✅ Keeps XXE vulnerability (for CTF)
✅ Keeps full HTML/CSS/JS UI intact
✅ No filesystem writes (Render safe)
⚠️ Do NOT use on public servers other than CTF sandboxes
"""

from flask import Flask, request, render_template_string, url_for
import os, secrets
from lxml import etree

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# --- UI Config ---
BG_IMG = "https://japanesesword.net/cdn/shop/articles/samurai_silhouette_1024x576.jpg?v=1745390010"
REMOTE_AUDIO = "https://www.mobiles24.co/metapreview.php?id=27018&cat=3&h=580887"
USE_LOCAL_AUDIO = False  # leave False for Render (no static writes)

# === Keep XXE enabled for CTF ===
ALLOW_EXTERNAL_ENTITIES = True  # ← this keeps the CTF behavior intact
# Render blocks network DTD fetches, but entity resolution still works locally

# === HTML Template (unchanged UI) ===
TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>— Samurai Scroll Portal</title>
  <link href="https://fonts.googleapis.com/css2?family=Sawarabi+Mincho&display=swap" rel="stylesheet">
  <style>
    :root{--accent:#e85b7b;--ink:#f8f6f4}
    html,body{height:100%;margin:0}
    body{
      font-family:'Sawarabi Mincho', system-ui, -apple-system, 'Segoe UI', Roboto, Arial;
      background-image: url("{{ bg_img }}");
      background-size: cover;
      background-position: center;
      color:var(--ink);
    }
    .veil{background:linear-gradient(rgba(2,6,23,0.78), rgba(2,6,23,0.78));min-height:100vh;padding:48px;}
    .portal{
      max-width:760px;margin:40px auto;padding:28px;border-radius:14px;
      background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
      box-shadow:0 8px 40px rgba(0,0,0,0.6);
      border: 1px solid rgba(255,255,255,0.03);
      text-align:center;
    }
    h1{margin:0 0 6px;font-size:2.1rem;letter-spacing:2px}
    p.lead{margin:0 0 18px;opacity:0.95}
    form{display:flex;gap:12px;align-items:center;justify-content:center}
    .file{flex:1;background:rgba(255,255,255,0.03);padding:10px 12px;border-radius:10px;border:1px dashed rgba(255,255,255,0.04);max-width:320px;}
    input[type=file]{background:transparent;color:var(--ink)}
    button.submit{background:transparent;border:1px solid var(--accent);color:var(--accent);padding:10px 14px;border-radius:10px;cursor:pointer}
    button.submit:hover{background:var(--accent);color:#fff}
    .result{margin-top:18px;padding:14px;border-radius:10px;background:rgba(0,0,0,0.35);}
    .blossom{position:fixed;right:12px;top:12px;opacity:0.9;pointer-events:none}
    .blossom svg{width:160px;height:160px}
    .samurai-cursor, form, button, a {
      cursor: url('data:image/svg+xml;utf8,<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 64 64"><g fill="none" stroke="%23000" stroke-width="1"><path d="M2 2 L18 18 L10 20 L26 36 L28 30 L44 46 L30 50 L34 36 L18 20 L26 18 Z" fill="%23ffffff" opacity="0.01"/><g transform="translate(6,6)"><path d="M4 0 L12 8 L6 10 L14 18" stroke="%23fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><rect x="0" y="18" width="6" height="6" rx="1" fill="%23999" stroke="%23fff"/></g></g></svg>') 6 6, auto;
    }
    footer{margin-top:28px;text-align:center;opacity:0.8;font-size:0.9rem}

    #mute-btn {
      position: fixed;
      left: 20px;
      bottom: 20px;
      background: rgba(0,0,0,0.45);
      color: var(--ink);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 1.1rem;
      cursor: pointer;
      display:none;
    }
    #mute-btn:hover{background:rgba(255,255,255,0.15);}
  </style>
</head>
<body>
  <div class="veil" id="veil">
    <div class="portal samurai-cursor">
      <h1>— Samurai Scroll Portal</h1>
      <p class="lead">Upload your scroll below and reveal your destiny</p>

      <form method="POST" enctype="multipart/form-data">
        <label class="file">
          <input type="file" name="scroll" required>
        </label>
        <button class="submit" type="submit">Unseal Scroll</button>
      </form>

      {% if xml_preview %}
        <div class="result">
          <h3>Portal Response</h3>
          <pre style="white-space:pre-wrap;word-break:break-word;color:#fee">{{ xml_preview }}</pre>
        </div>
      {% endif %}
      {% if secret_dump %}
        <div class="result">
          <h3>Whispers from the archive</h3>
          <pre style="white-space:pre-wrap;word-break:break-word;color:#ffdcdc">{{ secret_dump }}</pre>
        </div>
      {% endif %}
      <footer>— The Dojo Archives</footer>
    </div>

    <div class="blossom" aria-hidden="true">
      <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <g fill="#ffd7e6" stroke="#ff78a6" stroke-width="1">
          <path d="M100 10 C110 30,140 30,150 50 C130 55,120 80,100 90 C80 80,70 55,50 50 C60 30,90 30,100 10 Z"/>
          <circle cx="110" cy="60" r="6" fill="#ff8fb3"/>
        </g>
      </svg>
    </div>

    <audio id="bg-audio" src="{{ audio_src }}" loop></audio>
    <button id="mute-btn">🔊</button>
  </div>

  <script>
    const audio = document.getElementById('bg-audio');
    const muteBtn = document.getElementById('mute-btn');
    const veil = document.getElementById('veil');
    let hasPlayed = false;

    veil.addEventListener('click', () => {
      if (!hasPlayed) {
        hasPlayed = true;
        audio.volume = 0;
        audio.muted = false;
        audio.play().then(() => {
          muteBtn.style.display = 'block';
          let v = 0;
          const fade = setInterval(()=>{
            if(v<1){ v+=0.05; audio.volume=v; } else clearInterval(fade);
          },150);
        }).catch(err=>console.log('Audio play blocked',err));
      }
    });

    muteBtn.addEventListener('click', () => {
      if(audio.muted || audio.volume===0){
        audio.muted=false; audio.volume=1; muteBtn.textContent='🔊';
      } else {
        audio.muted=true; muteBtn.textContent='🔇';
      }
    });
  </script>
</body>
</html>'''

# === Flask Route ===
@app.route('/', methods=['GET','POST'])
def portal():
    xml_preview = None
    secret_dump = None
    if request.method == 'POST':
        f = request.files.get('scroll')
        if f:
            data = f.read()
            try:
                xml_preview = data.decode(errors='replace')[:2000]
            except Exception:
                xml_preview = '<binary data>'

            try:
                parser = etree.XMLParser(load_dtd=True, resolve_entities=True, no_network=False)
                root = etree.fromstring(data, parser=parser)
                name = root.findtext('name') or ''
                rank = root.findtext('rank') or ''
                quote = root.findtext('quote') or root.findtext('message') or ''
                parts = []
                if name: parts.append(f"Name: {name}")
                if rank: parts.append(f"Rank: {rank}")
                if quote: parts.append(f"Scroll: {quote}")
                secret_dump = "\\n".join(parts) if parts else None
            except Exception as e:
                xml_preview = (xml_preview or '') + f"\\n\\n(The portal could not fully bind the scroll.)\\n({e})"

    audio_src = url_for('static', filename='dojo.mp3') if USE_LOCAL_AUDIO else REMOTE_AUDIO
    return render_template_string(TEMPLATE, bg_img=BG_IMG, audio_src=audio_src,
                                  xml_preview=xml_preview, secret_dump=secret_dump)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 1337))
    app.run(host='0.0.0.0', port=port, debug=False)
