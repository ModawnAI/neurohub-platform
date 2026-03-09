# Hypoxic Burden Service (Node.js)

A pure Node.js implementation of the Hypoxic Burden calculation service for sleep apnea analysis.

## Overview

This service calculates Hypoxic Burden from SpO2, respiratory events, and sleep stage data using the algorithm published in:

> Sutherland K, Sadr N, Bin YS, et al. "Comparative associations of oximetry patterns in Obstructive Sleep Apnea with incident cardiovascular disease", *Sleep*, 2022. DOI: 10.1093/sleep/zsac179

## Features

- ✅ Pure Node.js implementation (no Python dependencies)
- ✅ RESTful API endpoint for HB calculation
- ✅ Interactive Plotly visualization
- ✅ Supports CSV data files with absolute time format (HH:MM:SS)
- ✅ Automatic time normalization and day-shift adjustment
- ✅ MATLAB-compliant algorithm implementation

## Installation

```bash
npm install
```

## Usage

### Start the Server

```bash
node hb-api-server.js
```

Server will run on http://localhost:8000

### API Endpoint

**POST** `/api/hb`

Upload files via multipart/form-data:
- `spo2`: SpO2 CSV file (columns: relative_time, absolute_time_HH:MM:SS, value)
- `eventlist`: Event list text file (Natus format, UTF-16)
- `hypn`: (optional) Hypnogram CSV file

**Response:**
```json
{
  "HB": 4.784,
  "SleepHour": 7.44,
  "t": [...],
  "spo2": [...],
  "events": [...],
  "avg": [...],
  "filt": [...]
}
```

### Web Interface

- **Home**: http://localhost:8000
- **Visualization**: http://localhost:8000/visualize
- **Health Check**: http://localhost:8000/health

## File Structure

```
hb-service/
├── hb-api-server.js      # Express server
├── hb-calculator.js      # Core HB calculation engine
├── package.json          # Dependencies
├── static/
│   ├── index.html        # Upload interface
│   ├── visualize.html    # Results visualization
│   └── hb.js            # Frontend logic
├── tmp/                  # Temporary uploaded files
└── uploads/              # File storage
```

## Algorithm Details

1. **Time Normalization**: Absolute times (HH:MM:SS) → unwrap midnight rollover → adjust day shift → normalize to t0
2. **Event Alignment**: Match events to SpO2 timeline with ±12hr correction
3. **Averaging**: Ensemble average around event endpoints with ±SD calculation
4. **Filtering**: 12-point moving average (matches MATLAB reference)
5. **HB Calculation**: Fixed window [-5, +45] seconds, area-under-curve integration

## Visualization

Two interactive Plotly charts:

1. **SpO2 Time Series**: Full recording with sleep stage hypnogram overlay and event markers
2. **Average SpO2 Response**: Ensemble averaged desaturation pattern with filtered curve

## Citation

Developed at the **Molecular Neuroimaging and Therapy (MoNET)** Laboratory  
**MoNET@Yonsei University College of Medicine**

Contact: monetbrain@gmail.com

© 2025 Hae-Jeong Park, Ph.D.

## License

Free to use with proper citation of the original publication (Sutherland et al., 2022).
