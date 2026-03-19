from pymavlink import mavutil
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ── Feature definitions ───────────────────────────────────────

FEATURES = ['VibeX', 'VibeY', 'VibeZ',
            'Volt',  'Curr',
            'Roll',  'Pitch',
            'C1',    'C2',    'C3',    'C4']

FEATURE_GROUPS = {
    'Motor'   : ['C1', 'C2', 'C3', 'C4'],
    'Battery' : ['Volt', 'Curr'],
    'Vibration': ['VibeX', 'VibeY', 'VibeZ'],
    'Attitude': ['Roll', 'Pitch'],
}

MOTOR_NAMES = {
    'C1': 'Motor 1',
    'C2': 'Motor 2',
    'C3': 'Motor 3',
    'C4': 'Motor 4'
}


# ── Step 1: Feature extraction ───────────────────────────────
def extract_features(filepath):
    """
    Extract raw sensor features from a .bin log file.
    No assumptions about what is normal or abnormal.
    """
    mlog        = mavutil.mavlink_connection(filepath)
    data        = []
    current_row = {}

    needed_types = ['VIBE', 'BAT', 'ATT', 'RCOU']

    
    seen = set()

    while True:
        msg = mlog.recv_match(
            type=needed_types,
            blocking=False
        )
        if msg is None:
            break

        t        = msg.TimeUS / 1e6
        msg_type = msg.get_type()

        if msg_type == 'VIBE':
            current_row['time']  = t
            current_row['VibeX'] = msg.VibeX
            current_row['VibeY'] = msg.VibeY
            current_row['VibeZ'] = msg.VibeZ
            seen.add('VIBE')

        elif msg_type == 'BAT':
            current_row['Volt'] = msg.Volt
            current_row['Curr'] = msg.Curr
            seen.add('BAT')

        elif msg_type == 'ATT':
            current_row['Roll']  = msg.Roll
            current_row['Pitch'] = msg.Pitch
            seen.add('ATT')

        elif msg_type == 'RCOU':
            current_row['C1'] = msg.C1
            current_row['C2'] = msg.C2
            current_row['C3'] = msg.C3
            current_row['C4'] = msg.C4
            seen.add('RCOU')

       
        if seen == set(needed_types):
            data.append(current_row.copy())
            current_row = {}
            seen        = set()

    df = pd.DataFrame(data)
    return df


# ── Step 2: Loading normal flights ───────────────────────────────

normal_files = [
    'vibe test no notch.bin',
    'after prop balance.bin',
    'VTOL hover with BDshot RPM.bin',
]

normal_dfs = []
for f in normal_files:
    df = extract_features(f)
    if len(df) > 0:
        normal_dfs.append(df)

normal_data = pd.concat(normal_dfs, ignore_index=True)
X_train     = normal_data[FEATURES].values


# ── Step 3: Training Isolation Forest ───────────────────────────

scaler         = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = IsolationForest(
    n_estimators=100,
    contamination=0.05,  
    random_state=42
)
model.fit(X_train_scaled)


train_scores     = model.decision_function(X_train_scaled)
normal_avg_score = np.mean(train_scores)
normal_std_score = np.std(train_scores)


# ── Step 4: Analyzing crash flight ─────────────────────────────

crash_file = 'transition.bin'
crash_df   = extract_features(crash_file)

X_crash        = crash_df[FEATURES].values
X_crash_scaled = scaler.transform(X_crash)


crash_scores      = model.decision_function(X_crash_scaled)
crash_predictions = model.predict(X_crash_scaled)

crash_df['anomaly_score'] = crash_scores
crash_df['is_anomaly']    = crash_predictions == -1


# ── Step 5: Calculating REAL confidence scores from data ───────


anomaly_mask  = crash_df['is_anomaly']
normal_mask   = ~crash_df['is_anomaly']

anomaly_rows  = crash_df[anomaly_mask][FEATURES]
normal_rows   = crash_df[normal_mask][FEATURES]


normal_mean   = normal_data[FEATURES].mean()
normal_std    = normal_data[FEATURES].std()
anomaly_mean  = anomaly_rows.mean()


z_scores      = ((anomaly_mean - normal_mean) / 
                  normal_std).abs()


def z_to_confidence(z):
    return min(round((1 - np.exp(-z * 0.8)) * 100, 1), 99.0)

feature_confidence = {
    f: z_to_confidence(z_scores[f]) 
    for f in FEATURES
}


group_confidence = {}
for group, features in FEATURE_GROUPS.items():
    available = [f for f in features if f in feature_confidence]
    if available:
        group_confidence[group] = max(
            feature_confidence[f] for f in available
        )


ranked_groups = sorted(
    group_confidence.items(),
    key=lambda x: x[1],
    reverse=True
)


motor_confidence = {
    f: feature_confidence[f]
    for f in FEATURE_GROUPS['Motor']
}
worst_motor     = max(motor_confidence, key=motor_confidence.get)
worst_motor_conf= motor_confidence[worst_motor]


# ── Step 6: Summary statistics ────────────────────────────────
total_points  = len(crash_df)
anomaly_count = anomaly_mask.sum()
anomaly_pct   = (anomaly_count / total_points) * 100

crash_avg_score = np.mean(crash_scores)
deviation_pct   = ((normal_avg_score - crash_avg_score) /
                    abs(normal_avg_score)) * 100

worst_moments   = crash_df.nsmallest(5, 'anomaly_score')
duration        = (crash_df['time'].iloc[-1] - 
                   crash_df['time'].iloc[0])


top_features = sorted(
    z_scores.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]


# ── Step 7: Printing conversational report ──────────────────────
print("\n")
print("╔══════════════════════════════════════════════════╗")
print("║      ArduPilot AI Flight Log Diagnosis           ║")
print("║      Model: Isolation Forest (Unsupervised ML)   ║")
print("╚══════════════════════════════════════════════════╝")

print(f"\n  Hi! I've finished analyzing your flight log.")
print(f"  Here's what I found:\n")

# ── About this flight
print(f"  ── ABOUT THIS FLIGHT ──────────────────────────")
print(f"  File         : {crash_file}")
print(f"  Flight time  : {duration:.1f}s "
      f"({duration/60:.1f} minutes)")
print(f"  Trained on   : {len(normal_files)} normal flights "
      f"({len(X_train)} timesteps)")
print(f"  Features     : {len(FEATURES)} sensor signals")
print(f"                 analyzed simultaneously")

# ── What the model found
print(f"\n  ── WHAT THE MODEL FOUND ───────────────────────")
print(f"  Anomalous moments : {anomaly_count} out of "
      f"{total_points} ({anomaly_pct:.1f}%)")
print(f"  Severity          : {deviation_pct:.1f}% worse "
      f"than your normal flights")

# ── Worst moments
print(f"\n  ── WORST MOMENTS IN THE FLIGHT ────────────────")
for _, row in worst_moments.iterrows():
    print(f"  🔴 t={row['time']:.1f}s  "
          f"anomaly score = {row['anomaly_score']:.4f}")

# ── Feature deviation — purely from data
print(f"\n  ── WHICH SENSORS DEVIATED MOST ────────────────")
print(f"  (Ranked by the model — no human ordering)")
for feature, z in top_features:
    conf = feature_confidence[feature]
    bar  = "█" * min(int(conf / 5), 20)
    print(f"  {feature:<8} {bar} "
          f"z={z:.2f}  confidence={conf}%")

# ── Root cause — ranked by model confidence
print(f"\n  ── WHAT LIKELY WENT WRONG ─────────────────────")
print(f"  (Ranked by model confidence — highest first)\n")

severity_icons = {
    range(80, 101): "🔴",
    range(60, 80) : "🟡",
    range(0,  60) : "🟢",
}

def get_icon(conf):
    for r, icon in severity_icons.items():
        if int(conf) in r:
            return icon
    return "🟢"

for group, conf in ranked_groups:
    icon = get_icon(conf)

    if group == 'Motor':
        print(f"  {icon} {group} Issue "
              f"— model confidence: {conf}%")
        print(f"     {MOTOR_NAMES[worst_motor]} showed the "
              f"most abnormal behavior")
        print(f"     ({worst_motor_conf}% confidence)")

    elif group == 'Battery':
        print(f"  {icon} {group} Stress "
              f"— model confidence: {conf}%")
        print(f"     Voltage/current patterns deviated")
        print(f"     from normal flight baseline")

    elif group == 'Vibration':
        print(f"  {icon} {group} Anomaly "
              f"— model confidence: {conf}%")
        print(f"     Vibration levels unusual compared")
        print(f"     to baseline flights")

    elif group == 'Attitude':
        print(f"  {icon} {group} Instability "
              f"— model confidence: {conf}%")
        print(f"     Roll/pitch showed abnormal patterns")
    print()

# ── Recommended actions
print(f"  ── WHAT YOU SHOULD DO ─────────────────────────")
top_group = ranked_groups[0][0]
if top_group == 'Motor':
    print(f"  → Inspect {MOTOR_NAMES[worst_motor]} "
          f"and its ESC first")
    print(f"     (highest confidence finding)")
elif top_group == 'Battery':
    print(f"  → Test battery health under load first")
    print(f"     (highest confidence finding)")
elif top_group == 'Vibration':
    print(f"  → Check propeller balance and motor mounts")
    print(f"     (highest confidence finding)")
print(f"  → Do not fly until issues are resolved")

# ── Overall assessment
print(f"\n  ── OVERALL ASSESSMENT ─────────────────────────")
print(f"  Normal flights avg score : {normal_avg_score:.4f}")
print(f"  This flight avg score    : {crash_avg_score:.4f}")
print(f"  Deviation from normal    : "
      f"{deviation_pct:.1f}% more anomalous")

if deviation_pct > 50:
    print(f"\n  ⚠️  This flight was SIGNIFICANTLY abnormal")
    print(f"      Recommend thorough inspection before")
    print(f"      attempting another flight.")
elif deviation_pct > 20:
    print(f"\n  ⚠️  This flight was MODERATELY abnormal")
    print(f"      Some issues detected — review carefully.")
else:
    print(f"\n  ✅ This flight appears within normal range")
    print(f"      No critical anomalies detected.")

print("\n╚══════════════════════════════════════════════════╝\n")