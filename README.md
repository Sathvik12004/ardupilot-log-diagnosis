# ArduPilot AI Flight Log Diagnosis Tool

An AI-assisted flight log analysis tool that automatically parses 
ArduPilot `.bin` logs, detects anomalies using unsupervised machine 
learning, and generates human-readable root-cause diagnosis reports.

## What It Does

- Parses ArduPilot `.bin` flight logs via pymavlink
- Trains an **Isolation Forest** model on normal flight data
- Detects anomalies across 11 sensor signals simultaneously
- Calculates real confidence scores from z-score statistics
- Compares multiple flights progressively to find degradation trends
- Generates conversational diagnosis reports with ranked root causes

## How It Works
```
Normal flight logs → Train Isolation Forest → Learn normal patterns
                                                      ↓
Crash flight log  → Score every timestep  → Find anomalies
                                                      ↓
                    Calculate z-scores    → Rank root causes
                                                      ↓
                    Generate report       → Plain English diagnosis
```

## Real Case Study

Analyzed a **QuadPlane TRI crash** across 4 flight logs.  
Model trained on 3 normal flights (4611 timesteps, 11 features).  
No hardcoded thresholds — everything learned from data.

| Flight | Duration | Anomaly Level | Verdict |
|--------|----------|--------------|---------|
| Vibe Test (No Notch) | 1.6 min | Baseline normal | Ground test |
| After Prop Balance | 1.9 min | Normal | Safe flight |
| VTOL Hover | 5.1 min | Normal | Safe flight |
| Transition | 7.7 min | 116.9% worse than normal | 💀 Crash |

### What the Model Found — Without Being Told

The Isolation Forest model, trained only on normal flights,
automatically identified:
- 85.6% of timesteps in the crash flight as anomalous
- Motor 4 (C4) as the most deviated motor signal
- Battery stress as a contributing factor
- Flight severity: 116.9% worse than normal baseline

## Sample Diagnosis Output
```
╔══════════════════════════════════════════════════╗
║      ArduPilot AI Flight Log Diagnosis           ║
║      Model: Isolation Forest (Unsupervised ML)   ║
╚══════════════════════════════════════════════════╝

  Hi! I've finished analyzing your flight log.
  Here's what I found:

  ── ABOUT THIS FLIGHT ──────────────────────────
  File         : transition.bin
  Flight time  : 463.4s (7.7 minutes)
  Trained on   : 3 normal flights (4611 timesteps)
  Features     : 11 sensor signals analyzed simultaneously

  ── WHAT THE MODEL FOUND ───────────────────────
  Anomalous moments : 3967 out of 4636 (85.6%)
  Severity          : 116.9% worse than normal flights

  ── WHAT LIKELY WENT WRONG ─────────────────────
  (Ranked by model confidence — highest first)

  🔴 Motor Issue — model confidence: 87.3%
     Motor 4 showed the most abnormal behavior

  🔴 Battery Stress — model confidence: 74.1%
     Voltage/current patterns deviated from baseline

  🟡 Vibration Anomaly — model confidence: 61.2%
     Vibration levels unusual compared to baseline
╚══════════════════════════════════════════════════╝
```

## Sample Output Plots

![Vibration Comparison](sample_output/vibration_comparison.png)
![Transition Analysis](sample_output/transition_spike_analysis.png)

## Installation
```bash
git clone https://github.com/Sathvik12004/ardupilot-log-diagnosis
cd ardupilot-log-diagnosis
pip install -r requirements.txt
```

## Usage
```bash
# Step 1 — Explore what message types are in your log
python explore_log.py

# Step 2 — Extract and analyze key signals
python extract_signals.py

# Step 3 — Compare vibration across multiple flights
python compare_vibes.py

# Step 4 — Rule-based anomaly detection (baseline)
python diagnose.py

# Step 5 — AI-powered anomaly detection (ML model)
python ml_diagnose.py
```

## Scripts

| Script | Purpose |
|--------|---------|
| `explore_log.py` | Lists all message types and counts in a .bin file |
| `extract_signals.py` | Extracts vibration, battery, and attitude signals |
| `compare_vibes.py` | Compares vibration across multiple flights |
| `diagnose.py` | Rule-based anomaly detection (baseline approach) |
| `ml_diagnose.py` | **Isolation Forest ML model — AI-powered detection** |

## Built For

GSoC 2026 — ArduPilot  
Project: AI-Assisted Log Diagnosis & Root-Cause Detection

## Author

Sathvik  
B.Tech ECE — Vignana Bharathi Institute of Technology (JNTUH)  
IEEE Publication: Vocal Lens — Accepted & Presented at IEEE ICoECIT 2026  
GitHub: github.com/Sathvik12004