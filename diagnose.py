from pymavlink import mavutil
import pandas as pd

def diagnose(filepath):
    mlog = mavutil.mavlink_connection(filepath)
    
    vibe_data = []
    bat_data  = []
    att_data  = []
    rcou_data = []
    msg_data  = []
    ev_data   = []

    while True:
        msg = mlog.recv_match(
            type=['VIBE','BAT','ATT','RCOU','MSG','EV'],
            blocking=False
        )
        if msg is None:
            break
        t        = msg.TimeUS / 1e6
        msg_type = msg.get_type()

        if msg_type == 'VIBE':
            vibe_data.append({'time': t, 'VibeX': msg.VibeX,
                              'VibeY': msg.VibeY, 'VibeZ': msg.VibeZ})
        elif msg_type == 'BAT':
            bat_data.append({'time': t, 'Volt': msg.Volt,
                             'Curr': msg.Curr})
        elif msg_type == 'ATT':
            att_data.append({'time': t, 'Roll': msg.Roll,
                             'Pitch': msg.Pitch, 'Yaw': msg.Yaw})
        elif msg_type == 'RCOU':
            rcou_data.append({'time': t, 'C1': msg.C1, 'C2': msg.C2,
                              'C3': msg.C3, 'C4': msg.C4})
        elif msg_type == 'MSG':
            msg_data.append({'time': t, 'text': msg.Message})
        elif msg_type == 'EV':
            ev_data.append({'time': t, 'id': msg.Id})

    vibe_df = pd.DataFrame(vibe_data)
    bat_df  = pd.DataFrame(bat_data)
    att_df  = pd.DataFrame(att_data)
    rcou_df = pd.DataFrame(rcou_data)

    anomalies = []

    # Check 1 — Vibration
    for axis in ['VibeX', 'VibeY', 'VibeZ']:
        if vibe_df[axis].max() > 30:
            t_peak = vibe_df.loc[vibe_df[axis].idxmax(), 'time']
            anomalies.append(
                f"HIGH VIBRATION: {axis} peaked at "
                f"{vibe_df[axis].max():.1f} m/s² at t={t_peak:.1f}s"
            )

    # Check 2 — Battery voltage
    if bat_df['Volt'].min() < 10.5:
        t_low = bat_df.loc[bat_df['Volt'].idxmin(), 'time']
        anomalies.append(
            f"LOW BATTERY: Voltage dropped to "
            f"{bat_df['Volt'].min():.2f}V at t={t_low:.1f}s"
        )

    # Check 3 — Battery oscillation
    bat_df['rolling_std'] = bat_df['Volt'].rolling(20).std()
    if bat_df['rolling_std'].max() > 0.5:
        t_osc = bat_df.loc[bat_df['rolling_std'].idxmax(), 'time']
        anomalies.append(
            f"BATTERY INSTABILITY: Voltage oscillating "
            f"at t={t_osc:.1f}s — possible ESC/motor stress"
        )

    # Check 4 — Extreme attitude
    if att_df['Roll'].abs().max() > 45:
        t_roll = att_df.loc[att_df['Roll'].abs().idxmax(), 'time']
        anomalies.append(
            f"EXTREME ROLL: {att_df['Roll'].abs().max():.1f}° "
            f"at t={t_roll:.1f}s"
        )
    if att_df['Pitch'].abs().max() > 45:
        t_pitch = att_df.loc[att_df['Pitch'].abs().idxmax(), 'time']
        anomalies.append(
            f"EXTREME PITCH: {att_df['Pitch'].abs().max():.1f}° "
            f"at t={t_pitch:.1f}s"
        )

    # Check 5 — Motor saturation and cutout
    for col, name in [('C1','Motor 1'),('C2','Motor 2'),
                      ('C3','Motor 3'),('C4','Motor 4')]:
        maxed = (rcou_df[col] >= 1950).sum()
        mined = (rcou_df[col] <= 1050).sum()
        if maxed > 50:
            anomalies.append(
                f"MOTOR SATURATION: {name} at maximum "
                f"PWM for {maxed} samples — fighting to compensate"
            )
        if mined > 50:
            anomalies.append(
                f"MOTOR CUTOUT: {name} at minimum "
                f"PWM for {mined} samples — possibly failed"
            )

    # ── Print Report ─────────────────────────────────────────
    duration = (vibe_df['time'].iloc[-1] -
                vibe_df['time'].iloc[0])

    print("\n")
    print("ArduPilot AI Log Diagnosis Report")
    print(f"  File          : {filepath}")
    print(f"  Duration      : {duration:.1f}s ({duration/60:.1f} min)")
    print(f"  Start Voltage : {bat_df['Volt'].iloc[0]:.2f}V")
    print(f"  End Voltage   : {bat_df['Volt'].iloc[-1]:.2f}V")
    print(f"  Max Current   : {bat_df['Curr'].max():.1f}A")
    print(f"  Max Roll      : {att_df['Roll'].abs().max():.1f}°")
    print(f"  Max Pitch     : {att_df['Pitch'].abs().max():.1f}°")

    print(f"\n  ANOMALIES DETECTED: {len(anomalies)}")
    print("  " + "─" * 46)
    if anomalies:
        for a in anomalies:
            print(f"  {a}")
    else:
        print("No anomalies detected")

    print("\n  ROOT CAUSE HYPOTHESIS:")
    print("  " + "─" * 46)
    if any('MOTOR CUTOUT' in a for a in anomalies):
        print("     Motor failure detected — one or more motors")
        print("     cut out during flight. Check ESC and motor")
        print("     connections before next flight.")
    if any('BATTERY INSTABILITY' in a for a in anomalies):
        print("     Battery under stress — voltage oscillations")
        print("     suggest motor compensation. Check battery")
        print("     health and C-rating.")
    if any('SATURATION' in a for a in anomalies):
        print("     Motor saturation — aircraft fighting to")
        print("     maintain attitude. Check balance and CG.")
    if not anomalies:
        print("     Flight appears normal — no critical issues")


# ── Run on all files ─────────────────────────────────────────
# Change these filenames to match your log files
for f in ['vibe test no notch.bin',
          'after prop balance.bin',
          'VTOL hover with BDshot RPM.bin',
          'transition.bin']:
    diagnose(f)