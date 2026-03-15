from pymavlink import mavutil
import pandas as pd
import matplotlib.pyplot as plt

mlog = mavutil.mavlink_connection('VTOL hover test.bin')

# Storage lists for each signal
vibe_data = []
bat_data  = []
ekf_data  = []
att_data  = []


while True:
    msg = mlog.recv_match(
        type=['VIBE', 'BAT', 'XKF4', 'ATT'],
        blocking=False
    )
    if msg is None:
        break

    t = msg.TimeUS / 1e6  
    msg_type = msg.get_type()

    if msg_type == 'VIBE':
        vibe_data.append({
            'time'  : t,
            'VibeX' : msg.VibeX,
            'VibeY' : msg.VibeY,
            'VibeZ' : msg.VibeZ,
        })

    elif msg_type == 'BAT':
        bat_data.append({
            'time'   : t,
            'Voltage': msg.Volt,
            'Current': msg.Curr,
        })

    elif msg_type == 'XKF4':
        ekf_data.append({
            'time' : t,
            'SV'   : msg.SV,
            'SP'   : msg.SP,
            'SH'   : msg.SH,
            'SM'   : msg.SM,
        })

    elif msg_type == 'ATT':
        att_data.append({
            'time' : t,
            'Roll' : msg.Roll,
            'Pitch': msg.Pitch,
            'Yaw'  : msg.Yaw,
        })

# Converts to DataFrames
vibe_df = pd.DataFrame(vibe_data)
bat_df  = pd.DataFrame(bat_data)
att_df  = pd.DataFrame(att_data)


# ── VIBRATION ANALYSIS ──────────────────────────────────────
print("=" * 50)
print("VIBRATION ANALYSIS")
print("=" * 50)
print(f"Max VibeX : {vibe_df['VibeX'].max():.2f}")
print(f"Max VibeY : {vibe_df['VibeY'].max():.2f}")
print(f"Max VibeZ : {vibe_df['VibeZ'].max():.2f}")
print(f"Avg VibeX : {vibe_df['VibeX'].mean():.2f}")
print(f"Avg VibeY : {vibe_df['VibeY'].mean():.2f}")
print(f"Avg VibeZ : {vibe_df['VibeZ'].mean():.2f}")

print("\n── Threshold Check (ArduPilot standard) ──")
print(f"VibeX safe? : {'YES' if vibe_df['VibeX'].max() < 30 else 'NO — too high!'}")
print(f"VibeY safe? : {'YES' if vibe_df['VibeY'].max() < 30 else 'NO — too high!'}")
print(f"VibeZ safe? : {'YES' if vibe_df['VibeZ'].max() < 30 else 'NO — too high!'}")

peak_vibe_time = vibe_df.loc[vibe_df['VibeZ'].idxmax(), 'time']
print(f"\nVibration peaked at : t={peak_vibe_time:.2f}s")

# ── BATTERY ANALYSIS ────────────────────────────────────────
print("\n" + "=" * 50)
print("BATTERY ANALYSIS")
print("=" * 50)
print(f"Starting voltage : {bat_df['Voltage'].iloc[0]:.2f}V")
print(f"Ending voltage   : {bat_df['Voltage'].iloc[-1]:.2f}V")
print(f"Minimum voltage  : {bat_df['Voltage'].min():.2f}V")
print(f"Maximum current  : {bat_df['Current'].max():.2f}A")

voltage_drop = bat_df['Voltage'].iloc[0] - bat_df['Voltage'].min()
print(f"Total voltage drop: {voltage_drop:.2f}V")
print(f"Battery safe?     : {'YES' if bat_df['Voltage'].min() > 10.5 else 'NO — voltage too low!'}")

low_voltage = bat_df[bat_df['Voltage'] < 10.5]
if not low_voltage.empty:
    print(f"Voltage went critical at: t={low_voltage.iloc[0]['time']:.2f}s")

# ── ATTITUDE ANALYSIS ───────────────────────────────────────
print("\n" + "=" * 50)
print("ATTITUDE ANALYSIS")
print("=" * 50)
print(f"Max Roll  : {att_df['Roll'].abs().max():.1f}°")
print(f"Max Pitch : {att_df['Pitch'].abs().max():.1f}°")

print(f"\nRoll safe?  : {'YES' if att_df['Roll'].abs().max() < 45 else 'NO — extreme roll!'}")
print(f"Pitch safe? : {'YES' if att_df['Pitch'].abs().max() < 45 else 'NO — extreme pitch!'}")

peak_roll_time = att_df.loc[att_df['Roll'].abs().idxmax(), 'time']
print(f"Max roll occurred at: t={peak_roll_time:.2f}s")