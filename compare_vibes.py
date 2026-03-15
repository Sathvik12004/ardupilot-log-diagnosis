from pymavlink import mavutil
import pandas as pd
import matplotlib.pyplot as plt

# ── Helper function ─────────────────────────────────────────
def extract_vibe(filepath):
    """Extract vibration data from a log file"""
    mlog = mavutil.mavlink_connection(filepath)
    data = []
    while True:
        msg = mlog.recv_match(type=['VIBE'], blocking=False)
        if msg is None:
            break
        data.append({
            'time'  : msg.TimeUS / 1e6,
            'VibeX' : msg.VibeX,
            'VibeY' : msg.VibeY,
            'VibeZ' : msg.VibeZ,
        })
    return pd.DataFrame(data)

# ── Load all files ───────────────────────────────────────────
# Change these file paths to match your log files
print("Loading all log files... please wait")

files = {
    'No Notch Filter' : 'vibe test no notch.bin',
    'After Prop Bal'  : 'after prop balance.bin',
    'VTOL Hover'      : 'VTOL hover with BDshot RPM.bin',
    'Transition'      : 'transition.bin',
}

vibes = {}
for label, filepath in files.items():
    print(f"  Reading {filepath}...")
    vibes[label] = extract_vibe(filepath)

print("Done!\n")

# ── Print comparison table ───────────────────────────────────
print("=" * 65)
print(f"{'Flight':<20} {'MaxX':>8} {'MaxY':>8} {'MaxZ':>8} {'AvgZ':>8} {'Safe?':>8}")
print("=" * 65)

THRESHOLD = 30  # ArduPilot recommended limit

for label, df in vibes.items():
    maxX = df['VibeX'].max()
    maxY = df['VibeY'].max()
    maxZ = df['VibeZ'].max()
    avgZ = df['VibeZ'].mean()
    safe = "YES" if maxZ < THRESHOLD else "NO"
    print(f"{label:<20} {maxX:>8.2f} {maxY:>8.2f} {maxZ:>8.2f} {avgZ:>8.2f} {safe:>8}")

print("=" * 65)
print(f"  Threshold: anything above {THRESHOLD} m/s² is considered unsafe")

# ── Plot vibration over time ─────────────────────────────────
fig, axes = plt.subplots(4, 1, figsize=(12, 10))
fig.suptitle('Vibration Comparison Across All Flights', fontsize=14)

for i, (label, df) in enumerate(vibes.items()):
    ax = axes[i]
    # Normalize time to start from 0 for each flight
    t = df['time'] - df['time'].iloc[0]
    ax.plot(t, df['VibeX'], alpha=0.6, label='VibeX', color='blue')
    ax.plot(t, df['VibeY'], alpha=0.6, label='VibeY', color='green')
    ax.plot(t, df['VibeZ'], alpha=0.9, label='VibeZ', color='red')
    ax.axhline(y=THRESHOLD, color='black', linestyle='--',
               linewidth=1, label='Safe limit (30)')
    ax.set_title(label)
    ax.set_ylabel('Vibration (m/s²)')
    ax.legend(loc='upper right', fontsize=8)
    ax.set_ylim(0, max(60, df['VibeZ'].max() + 10))
    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel('Time (seconds)')
plt.tight_layout()
plt.savefig('vibration_comparison.png', dpi=150)
plt.show()
print("\n Plot saved as vibration_comparison.png")