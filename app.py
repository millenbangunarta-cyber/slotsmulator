# app.py
"""
Slot Machine Simulator — Lucu & Cerah
Versi final untuk Streamlit Cloud
Fitur:
- Simulator play-money (tidak untuk judi uang nyata)
- Riwayat spin (tabel + unduh CSV)
- Animasi gulungan
- Mode Auto-Spin
- Tampilan lucu/cerah dengan emoji
Requirements: streamlit, pillow, pandas
"""

import streamlit as st
import random
import time
import io
import math
import wave
import struct
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Slot — Lucu & Cerah", page_icon="🍒", layout="centered")

# -------------------------
# Config & Constants
# -------------------------
SYMBOLS = ["🍒", "🔔", "🍋", "💎", "7️⃣", "🍀", "🍉"]
PAYOUT_TABLE = {
    "🍒": 5,
    "🔔": 8,
    "🍋": 4,
    "💎": 12,
    "7️⃣": 50,
    "🍀": 10,
    "🍉": 6,
}
START_BALANCE = 1000

# -------------------------
# Sound helpers (generate WAV bytes)
# -------------------------
def generate_sine_wav(freq=440.0, duration=0.2, volume=0.5, framerate=22050):
    n_samples = int(framerate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        for i in range(n_samples):
            t = float(i) / framerate
            val = volume * math.sin(2.0 * math.pi * freq * t)
            data = struct.pack('<h', int(val * 32767.0))
            wf.writeframesraw(data)
    buf.seek(0)
    return buf.read()

def generate_spin_sound():
    chunks = []
    freqs = [800, 700, 600, 500, 400]
    for f in freqs:
        chunks.append(generate_sine_wav(freq=f, duration=0.03, volume=0.15))
    return b"".join(chunks)

def generate_win_sound():
    chunks = []
    freqs = [520, 640, 780]
    for f in freqs:
        chunks.append(generate_sine_wav(freq=f, duration=0.12, volume=0.22))
    return b"".join(chunks)

SPIN_SOUND = generate_spin_sound()
WIN_SOUND = generate_win_sound()

# -------------------------
# Image helpers (render reels safely)
# -------------------------
def render_reels_as_image(reels, width=540, height=160, bg=(255, 255, 245)):
    im = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(im)

    font = ImageFont.load_default()  # font default supaya aman di Linux/Cloud

    box_w = (width - 40) // 3
    gap = 10
    x = 20
    for symbol in reels:
        rect = (x, 12, x + box_w, height - 12)
        draw.rounded_rectangle(rect, radius=12, fill=(255, 255, 255))
        # posisi simbol perkiraan, tidak pakai textsize()
        tx = x + box_w // 4
        ty = height // 4
        draw.text((tx, ty), symbol, font=font, fill=(20, 20, 20))
        x += box_w + gap

    draw.rectangle((0, 0, width - 1, height - 1), outline=(230, 180, 255))
    return im

# -------------------------
# Game logic
# -------------------------
def spin_once():
    return [random.choice(SYMBOLS) for _ in range(3)]

def evaluate_spin(reels, bet):
    if reels[0] == reels[1] == reels[2]:
        sym = reels[0]
        multiplier = PAYOUT_TABLE.get(sym, 0)
        win = bet * multiplier
        return int(win), f"🎉 Three {sym}! You win {win} coins."
    if reels[0] == reels[1] or reels[0] == reels[2] or reels[1] == reels[2]:
        win = int(bet * 1.5)
        return int(win), f"🙂 Two of a kind — you win {win} coins."
    return 0, "😞 No match — try again."

# -------------------------
# Init session state
# -------------------------
def init_state():
    st.session_state.setdefault("balance", START_BALANCE)
    st.session_state.setdefault("last_reels", ["-", "-", "-"])
    st.session_state.setdefault("last_bet", 0)
    st.session_state.setdefault("message", "Selamat datang! Gunakan koin mainan untuk bermain.")
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("auto_running", False)

init_state()

# -------------------------
# Layout
# -------------------------
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg,#fff8f0,#fff); }
    .accent { color: #ff6fb5; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🍒 Slot Machine — Lucu & Cerah")
st.markdown("**Simulator (play-money)** · Tanpa uang nyata · Untuk edukasi & hiburan")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Reels")
    img_placeholder = st.empty()
    img = render_reels_as_image(st.session_state.last_reels)
    img_placeholder.image(img, use_column_width=True)

    st.markdown("**Hasil**")
    st.info(st.session_state.message)

with col_right:
    st.subheader("Kontrol")
    st.markdown(f"**Saldo:** <span class='accent'>{st.session_state.balance} coins</span>", unsafe_allow_html=True)
    bet = st.number_input("Taruhan (coins)", min_value=1, max_value=max(1, st.session_state.balance), value=10, step=1)
    spin_speed = st.slider("Kecepatan animasi (detik per frame)", 0.03, 0.3, 0.09, step=0.01)
    animation_frames = st.slider("Jumlah frame animasi", 4, 20, 9, step=1)

    st.markdown("---")
    st.subheader("Auto-Spin")
    auto_spin = st.checkbox("Aktifkan Auto-Spin")
    auto_count = st.number_input("Jumlah putaran (Auto)", min_value=1, max_value=1000, value=10, step=1)
    auto_delay = st.slider("Delay antar putaran (s)", 0.1, 2.0, 0.5, step=0.1)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        spin_btn = st.button("Spin 🎰")
    with col_b:
        auto_btn = st.button("Start Auto" if not st.session_state.auto_running else "Stop Auto")

    st.markdown("---")
    if st.button("Reset Saldo (kembali ke 1000)"):
        st.session_state.balance = START_BALANCE
        st.session_state.history = []
        st.session_state.message = "Saldo direset ke 1000 coins."
        st.session_state.last_reels = ["-", "-", "-"]
        img_placeholder.image(render_reels_as_image(st.session_state.last_reels), use_column_width=True)

    if st.button("Unduh Riwayat (CSV)"):
        df = pd.DataFrame(st.session_state.history)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="slot_history.csv", mime="text/csv")

# -------------------------
# Spin functions
# -------------------------
def do_spin(bet_amount, frames=9, speed=0.08, play_sounds=True):
    if bet_amount > st.session_state.balance:
        st.warning("Saldo tidak cukup untuk taruhan tersebut.")
        return
    st.session_state.last_bet = bet_amount
    st.session_state.balance -= bet_amount
    for i in range(frames):
        tmp = [random.choice(SYMBOLS) for _ in range(3)]
        img = render_reels_as_image(tmp)
        img_placeholder.image(img, use_column_width=True)
        if play_sounds:
            st.audio(SPIN_SOUND, format="audio/wav")
        time.sleep(speed)
    final = spin_once()
    st.session_state.last_reels = final
    img_placeholder.image(render_reels_as_image(final), use_column_width=True)
    win, msg = evaluate_spin(final, bet_amount)
    if win > 0:
        st.session_state.balance += win
        if play_sounds:
            st.audio(WIN_SOUND, format="audio/wav")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_full = f"{msg} (Taruhan: {bet_amount}) · Saldo sekarang: {st.session_state.balance}"
    st.session_state.message = msg_full
    st.session_state.history.insert(0, {
        "timestamp": now,
        "reels": " ".join(final),
        "bet": bet_amount,
        "win": win,
        "balance_after": st.session_state.balance,
        "message": msg
    })

# -------------------------
# Handle interactions
# -------------------------
if 'action_in_progress' not in st.session_state:
    st.session_state['action_in_progress'] = False

if spin_btn and not st.session_state.action_in_progress:
    st.session_state.action_in_progress = True
    if bet <= 0:
        st.warning("Taruhan harus lebih dari 0.")
    elif bet > st.session_state.balance:
        st.warning("Saldo tidak cukup.")
    else:
        do_spin(bet, frames=animation_frames, speed=spin_speed, play_sounds=True)
    st.session_state.action_in_progress = False

if auto_btn:
    st.session_state.auto_running = not st.session_state.auto_running

if st.session_state.auto_running:
    st.session_state.action_in_progress = True
    spins_done = 0
    for i in range(int(auto_count)):
        if st.session_state.balance <= 0:
            st.warning("Saldo habis. Auto-Spin berhenti.")
            break
        do_spin(bet, frames=animation_frames, speed=spin_speed, play_sounds=True)
        spins_done += 1
        if not st.session_state.auto_running:
            break
        time.sleep(auto_delay)
    st.session_state.auto_running = False
    st.session_state.action_in_progress = False
    st.success(f"Auto-Spin selesai ({spins_done} putaran).")

# -------------------------
# Show history
# -------------------------
st.markdown("---")
st.subheader("📜 Riwayat Spin")
if len(st.session_state.history) == 0:
    st.info("Belum ada riwayat — mainkan dulu beberapa putaran!")
else:
    df_hist = pd.DataFrame(st.session_state.history)
    with st.expander("Tampilkan riwayat (klik untuk buka)"):
        st.dataframe(df_hist, use_container_width=True)

st.markdown("---")
st.markdown(
    """
    **Catatan penting:**  
    - Aplikasi ini **hanya simulator** menggunakan koin mainan — tidak ada uang nyata.  
    - Jangan gunakan aplikasi ini untuk aktivitas perjudian berbayar.  
    - Bisa dikembangkan dengan simbol tambahan, grafis custom, mode turnamen play-money.
    """
)
