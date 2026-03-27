import requests
import json
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
import os
import urllib.request
import tempfile

load_dotenv()

# --- Download and register Inter font ---
font_url = "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"
font_path = os.path.join(tempfile.gettempdir(), "Inter.ttf")
if not os.path.exists(font_path):
    print("Downloading Inter font...")
    urllib.request.urlretrieve(font_url, font_path)
fm.fontManager.addfont(font_path)
FONT = fm.FontProperties(fname=font_path).get_name()

# --- Fetch data ---
url = "https://nextgen.owldms.com/public_api/Data"

headers = {
    "accept": "application/json",
    "X-API-Key": os.getenv("API_KEY")
}

params = {
    "startDate": int(time.time()) - (3 * 86400),
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

# --- Parse the nested payload ---
parsed = []
for entry in data:
    try:
        payload = json.loads(entry["payload"]["Payload"])
        if "C" not in payload:
            continue
        parsed.append({
            "timestamp": datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")),
            "C": payload["C"],
            "T": payload.get("T", 0),
            "P": payload.get("P", 0),
            "BV": payload.get("BV", 0),
            "BP": payload.get("BP", 0),
            "FM": payload.get("FM", 0),
            "BT": payload.get("BT", 0),
        })
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Skipping entry: {e}")
        continue

parsed.sort(key=lambda x: x["timestamp"])

# --- Use all data ---
newest_streak = parsed

# --- Build a 5-minute time grid ---
# Fill missing slots with zeros so gaps show as drops
from datetime import timedelta

start_time = newest_streak[0]["timestamp"]
end_time = newest_streak[-1]["timestamp"]

# Round start down and end up to nearest 5 min
start_time = start_time.replace(second=0, microsecond=0)
start_time = start_time - timedelta(minutes=start_time.minute % 5)

# Build lookup dict keyed on rounded timestamp
def round_to_5min(dt):
    return dt.replace(second=0, microsecond=0) - timedelta(minutes=dt.minute % 5)

data_lookup = {}
for p in newest_streak:
    key = round_to_5min(p["timestamp"])
    data_lookup[key] = p  # If multiple readings in same slot, last one wins

# Generate every 5-min slot
grid = []
current = start_time
while current <= end_time:
    if current in data_lookup:
        grid.append(data_lookup[current])
    else:
        grid.append({
            "timestamp": current,
            "C": 0, "T": 0, "P": 0, "BV": 0, "BP": 0, "FM": 0, "BT": 0
        })
    current += timedelta(minutes=5)

newest_streak = grid

print(f"Newest streak: {len(newest_streak)} messages")
print(f"From: {newest_streak[0]['timestamp']}")
print(f"To:   {newest_streak[-1]['timestamp']}")

# --- Data arrays ---
timestamps = [p["timestamp"] for p in newest_streak]
temps = np.array([p["T"] for p in newest_streak])
pressures = np.array([p["P"] / 100 for p in newest_streak])
voltages = np.array([p["BV"] for p in newest_streak])
batt_pcts = np.array([p["BP"] for p in newest_streak])
free_mem = np.array([p["FM"] / 1000 for p in newest_streak])  # Convert to KB
counts = np.array([p["C"] for p in newest_streak])
board_temps = np.array([p["BT"] for p in newest_streak])

# =============================================
# Theme
# =============================================
BG = "#FAFAF8"
CARD_BG = "#FFFFFF"
GRID_COLOR = "#EEECEA"
BORDER = "#E0DDD8"

TEXT_PRIMARY = "#1A1915"
TEXT_SECONDARY = "#6E6B65"
TEXT_TERTIARY = "#A8A49E"

TERRACOTTA = "#C4603C"
WARM_BLUE = "#4A7CA8"
SAGE = "#508068"
SAND = "#B8912E"
ROSE = "#B5485F"

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 11,
})

def pad_lim(vals, pct=0.1):
    vmin, vmax = vals.min(), vals.max()
    m = (vmax - vmin) * pct
    if m == 0:
        m = 1
    return vmin - m, vmax + m

# =============================================
# Build figure with subplots
# =============================================
fig, (ax_env, ax_bat, ax_sys) = plt.subplots(
    3, 1, figsize=(14, 13), sharex=True, facecolor=BG,
    gridspec_kw={"hspace": 0.4}
)

# =============================================
# Title — using suptitle so it never collides
# =============================================
fig.suptitle("Device Telemetry", fontsize=26, fontweight="bold",
             color=TEXT_PRIMARY, fontfamily=FONT, x=0.12, ha="left", y=0.98)

fig.text(0.12, 0.945,
         f"TONEDTG5   ·   {len(newest_streak)} readings   ·   "
         f"{newest_streak[0]['timestamp'].strftime('%b %d, %Y %H:%M')} – "
         f"{newest_streak[-1]['timestamp'].strftime('%b %d, %Y %H:%M')}",
         fontsize=11, color=TEXT_SECONDARY, fontfamily=FONT, va="top")

# =============================================
# Panel 1 — Environment
# =============================================
ax_env.set_facecolor(CARD_BG)
ax_env.set_title("Environment", fontsize=15, fontweight="bold",
                 color=TEXT_PRIMARY, loc="left", pad=12, fontfamily=FONT)

# Temperature
ln1 = ax_env.plot(timestamps, temps, color=TERRACOTTA, linewidth=2,
                  label="Temperature (°F)", solid_capstyle="round", zorder=3)
ax_env.fill_between(timestamps, temps, alpha=0.1, color=TERRACOTTA, zorder=2)

# Board temperature
ln1b = ax_env.plot(timestamps, board_temps, color=ROSE, linewidth=1.8,
                   label="Board temp (°F)", solid_capstyle="round",
                   linestyle=(0, (5, 3)), zorder=3, alpha=0.85)

ax_env.set_ylabel("Temperature (°F)", fontsize=11, color=TERRACOTTA,
                   fontfamily=FONT, fontweight="bold", labelpad=14)
ax_env.tick_params(axis="y", colors=TERRACOTTA, labelsize=10, length=0, pad=8)
# Scale to fit both temp ranges
all_temps = np.concatenate([temps, board_temps])
ax_env.set_ylim(*pad_lim(all_temps))

# Pressure
ax_p = ax_env.twinx()
ln2 = ax_p.plot(timestamps, pressures, color=WARM_BLUE, linewidth=2,
                label="Pressure (hPa)", solid_capstyle="round", zorder=3)
ax_p.fill_between(timestamps, pressures, alpha=0.07, color=WARM_BLUE, zorder=2)
ax_p.set_ylabel("Pressure (hPa)", fontsize=11, color=WARM_BLUE,
                 fontfamily=FONT, fontweight="bold", labelpad=14)
ax_p.tick_params(axis="y", colors=WARM_BLUE, labelsize=10, length=0, pad=8)
ax_p.set_ylim(*pad_lim(pressures))

# Endpoint dots
for ax, ts, vals, c in [(ax_env, timestamps, temps, TERRACOTTA),
                         (ax_env, timestamps, board_temps, ROSE),
                         (ax_p, timestamps, pressures, WARM_BLUE)]:

    ax.scatter([ts[-1]], [vals[-1]], color=c, s=35, zorder=5,
               edgecolors=CARD_BG, linewidths=1.5)
    ax.scatter([ts[-1]], [vals[-1]], color=c, s=10, zorder=6)

# Legend — centered below the environment chart
lines_env = ln1 + ln1b + ln2
labels_env = [l.get_label() for l in lines_env]
ax_env.legend(lines_env, labels_env, loc="lower center",
              bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=10,
              labelcolor=TEXT_SECONDARY, frameon=False, handlelength=2,
              columnspacing=3)

# =============================================
# Panel 2 — Battery
# =============================================
ax_bat.set_facecolor(CARD_BG)
ax_bat.set_title("Battery", fontsize=15, fontweight="bold",
                 color=TEXT_PRIMARY, loc="left", pad=12, fontfamily=FONT)

# Voltage
ln3 = ax_bat.plot(timestamps, voltages, color=SAGE, linewidth=2,
                  label="Voltage (V)", solid_capstyle="round", zorder=3)
ax_bat.fill_between(timestamps, voltages, alpha=0.1, color=SAGE, zorder=2)
ax_bat.set_ylabel("Voltage (V)", fontsize=11, color=SAGE,
                   fontfamily=FONT, fontweight="bold", labelpad=14)
ax_bat.tick_params(axis="y", colors=SAGE, labelsize=10, length=0, pad=8)
ax_bat.set_ylim(*pad_lim(voltages))

# Battery %
ax_bp = ax_bat.twinx()
ln4 = ax_bp.plot(timestamps, batt_pcts, color=SAND, linewidth=2,
                 label="Battery %", solid_capstyle="round",
                 linestyle=(0, (5, 3)), zorder=3)
ax_bp.set_ylabel("Battery %", fontsize=11, color=SAND,
                  fontfamily=FONT, fontweight="bold", labelpad=14)
ax_bp.tick_params(axis="y", colors=SAND, labelsize=10, length=0, pad=8)
ax_bp.set_ylim(*pad_lim(batt_pcts))

# Endpoint dots
for ax, ts, vals, c in [(ax_bat, timestamps, voltages, SAGE),
                         (ax_bp, timestamps, batt_pcts, SAND)]:
    ax.scatter([ts[-1]], [vals[-1]], color=c, s=35, zorder=5,
               edgecolors=CARD_BG, linewidths=1.5)
    ax.scatter([ts[-1]], [vals[-1]], color=c, s=10, zorder=6)

# Legend — centered below the battery chart
lines_bat = ln3 + ln4
labels_bat = [l.get_label() for l in lines_bat]
ax_bat.legend(lines_bat, labels_bat, loc="lower center",
              bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=10,
              labelcolor=TEXT_SECONDARY, frameon=False, handlelength=2,
              columnspacing=3)

# =============================================
# Panel 3 — System
# =============================================
PLUM = "#7B6B8A"
INDIGO = "#5B6AAF"

ax_sys.set_facecolor(CARD_BG)
ax_sys.set_title("System", fontsize=15, fontweight="bold",
                 color=TEXT_PRIMARY, loc="left", pad=12, fontfamily=FONT)

# Free memory
ln5 = ax_sys.plot(timestamps, free_mem, color=PLUM, linewidth=2,
                  label="Free memory (KB)", solid_capstyle="round", zorder=3)
ax_sys.fill_between(timestamps, free_mem, alpha=0.1, color=PLUM, zorder=2)
ax_sys.set_ylabel("Free memory (KB)", fontsize=11, color=PLUM,
                   fontfamily=FONT, fontweight="bold", labelpad=14)
ax_sys.tick_params(axis="y", colors=PLUM, labelsize=10, length=0, pad=8)
ax_sys.set_ylim(*pad_lim(free_mem))

# Message count
ax_ct = ax_sys.twinx()
ln6 = ax_ct.plot(timestamps, counts, color=INDIGO, linewidth=2,
                 label="Message count", solid_capstyle="round",
                 linestyle=(0, (5, 3)), zorder=3)
ax_ct.set_ylabel("Message count", fontsize=11, color=INDIGO,
                  fontfamily=FONT, fontweight="bold", labelpad=14)
ax_ct.tick_params(axis="y", colors=INDIGO, labelsize=10, length=0, pad=8)
ax_ct.set_ylim(*pad_lim(counts))

# Endpoint dots
for ax, ts, vals, c in [(ax_sys, timestamps, free_mem, PLUM),
                         (ax_ct, timestamps, counts, INDIGO)]:
    ax.scatter([ts[-1]], [vals[-1]], color=c, s=35, zorder=5,
               edgecolors=CARD_BG, linewidths=1.5)
    ax.scatter([ts[-1]], [vals[-1]], color=c, s=10, zorder=6)

# Legend — centered below the system chart
lines_sys = ln5 + ln6
labels_sys = [l.get_label() for l in lines_sys]
ax_sys.legend(lines_sys, labels_sys, loc="lower center",
              bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=10,
              labelcolor=TEXT_SECONDARY, frameon=False, handlelength=2,
              columnspacing=3)

# =============================================
# Global styling
# =============================================
for ax in [ax_env, ax_p, ax_bat, ax_bp, ax_sys, ax_ct]:
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_color(BORDER)
    ax.spines["left"].set_color(BORDER)
    ax.spines["right"].set_color(BORDER)
    for s in ax.spines.values():
        s.set_linewidth(0.5)
    ax.grid(True, color=GRID_COLOR, linewidth=0.4, zorder=0)

# X-axis on bottom chart
ax_sys.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))
ax_sys.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
ax_sys.tick_params(axis="x", labelsize=10, length=0, pad=10, colors=TEXT_TERTIARY)

# Footer
fig.text(0.88, 0.005, "ClusterDuck Protocol", fontsize=8,
         color=TEXT_TERTIARY, ha="right", fontfamily=FONT, style="italic")

# Use tight_layout but leave room at top for title
fig.tight_layout(rect=[0.02, 0.03, 0.98, 0.93])

plt.savefig("telemetry.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.show()