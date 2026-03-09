/**
 * Standalone Node.js API Server for Hypoxic Burden Calculation
 * This replaces the Python FastAPI service (app.py) with a pure JavaScript solution
 * Uses the calculation logic from hb.js
 */

import express from 'express';
import multer from 'multer';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import morgan from 'morgan';
import { computeHypoxicBurdenFromFiles } from './hb-calculator.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Setup logging
const accessLogStream = fs.createWriteStream(path.join(__dirname, 'access.log'), { flags: 'a' });
app.use(morgan(':remote-addr - :remote-user [:date[clf]] ":method :url HTTP/:http-version" :status :res[content-length] ":referrer" ":user-agent" :response-time ms', { stream: accessLogStream }));

// Create necessary directories
const UPLOAD_DIR = path.join(__dirname, 'tmp');
const DATA_DIR = path.join(__dirname, 'data');
const STATIC_DIR = path.join(__dirname, 'static');
fs.mkdirSync(UPLOAD_DIR, { recursive: true });
fs.mkdirSync(DATA_DIR, { recursive: true });

// Serve static files
app.use('/static', express.static(STATIC_DIR));
app.use(express.json());

// Multer configuration for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    // Create unique folder name based on timestamp
    const timestamp = Date.now();
    const date = new Date(timestamp);
    const folderName = date.toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const uploadPath = path.join(DATA_DIR, folderName);
    fs.mkdirSync(uploadPath, { recursive: true });
    
    // Store the folder path for later use
    req.uploadFolder = uploadPath;
    cb(null, uploadPath);
  },
  filename: (req, file, cb) => {
    // Use specific filenames based on field name
    const filenameMap = {
      'spo2': 'o2sa.csv',
      'eventlist': 'eventlist.txt',
      'hypn': 'hypnogram.csv'
    };
    const filename = filenameMap[file.fieldname] || file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, filename);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB limit
});

// Root endpoint - serve the main HTML page
app.get('/', (req, res) => {
  res.sendFile(path.join(STATIC_DIR, 'index.html'));
});

// Main API endpoint - calculate hypoxic burden
app.post('/api/hb', 
  upload.fields([
    { name: 'spo2', maxCount: 1 },
    { name: 'eventlist', maxCount: 1 },
    { name: 'hypn', maxCount: 1 }
  ]),
  async (req, res) => {
    try {
      // Check required files
      if (!req.files || !req.files.spo2 || !req.files.eventlist) {
        return res.status(400).json({
          error: 'Missing required files. Please upload both spo2 and eventlist files.'
        });
      }

      const spo2Path = req.files.spo2[0].path;
      const eventlistPath = req.files.eventlist[0].path;
      const hypnPath = req.files.hypn?.[0]?.path || null;

      // Get the upload folder path (set by multer destination function)
      const uploadFolder = req.uploadFolder;
      const folderName = path.basename(uploadFolder);

      console.log(`[INFO] Processing files in folder: ${folderName}
        SpO2: ${spo2Path}
        EventList: ${eventlistPath}
        Hypnogram: ${hypnPath || 'Not provided'}`);

      const startTime = Date.now();

      // Calculate hypoxic burden using the JavaScript implementation
      const result = await computeHypoxicBurdenFromFiles(
        spo2Path,
        eventlistPath,
        hypnPath
      );

      // Generate and save HTML report to the same folder
      try {
        const htmlContent = generateHTMLReport(result);
        const htmlPath = path.join(uploadFolder, 'analysis_report.html');
        fs.writeFileSync(htmlPath, htmlContent);
        console.log(`[INFO] HTML report saved to: ${htmlPath}`);
      } catch (htmlErr) {
        console.warn('[WARN] Could not save HTML report:', htmlErr.message);
      }

      // Return JSON response with folder information
      const response = {
        ...result,
        folder: folderName,
        files: {
          spo2: 'o2sa.csv',
          eventlist: 'eventlist.txt',
          hypnogram: hypnPath ? 'hypnogram.csv' : null,
          report: 'analysis_report.html'
        }
      };

      const duration = Date.now() - startTime;
      console.log(`[INFO] Calculation completed in ${duration}ms for folder: ${folderName}, HB: ${result.hypoxicBurden?.toFixed(2) || 'N/A'}, Events: ${result.events?.length || 0}`);

      res.json(response);

    } catch (error) {
      console.error('[ERROR]', error);
      
      // Clean up files on error
      try {
        if (req.files) {
          Object.values(req.files).flat().forEach(file => {
            if (fs.existsSync(file.path)) fs.unlinkSync(file.path);
          });
        }
      } catch (cleanupErr) {
        console.warn('[WARN] Cleanup failed:', cleanupErr.message);
      }

      res.status(500).json({
        error: error.message || 'Internal server error during hypoxic burden calculation'
      });
    }
  }
);

// Download endpoint for generated reports
app.get('/download/:fname', (req, res) => {
  const filename = req.params.fname;
  const filepath = path.join(UPLOAD_DIR, filename);

  if (!fs.existsSync(filepath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  res.download(filepath, filename, (err) => {
    if (err) {
      console.error('[ERROR] Download failed:', err);
      if (!res.headersSent) {
        res.status(500).json({ error: 'Download failed' });
      }
    }
  });
});

// Visualization page
app.get('/visualize', (req, res) => {
  res.sendFile(path.join(STATIC_DIR, 'visualize.html'));
});

// Root route - redirect to visualize
app.get('/', (req, res) => {
  res.redirect('/visualize');
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Hypoxic Burden API',
    version: '2.0.0',
    runtime: 'Node.js'
  });
});

// Generate HTML report with embedded charts
function generateHTMLReport(data) {
  const date = new Date().toISOString().slice(0,10);
  const spo2ChartDiv = '<div id="chart1"></div>';
  const avgChartDiv = '<div id="chart2"></div>';

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hypoxic Burden Analysis Report - ${date}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
            background: #fff;
            color: #2d3748;
        }
        h1 { color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 15px; }
        h2 { color: #4a5568; margin-top: 40px; border-left: 4px solid #667eea; padding-left: 15px; }
        .header { text-align: center; margin-bottom: 50px; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .metric-label { font-size: 0.9em; opacity: 0.9; margin-bottom: 8px; }
        .metric-value { font-size: 2.5em; font-weight: bold; margin: 10px 0; }
        .metric-unit { font-size: 0.85em; opacity: 0.85; }
        .chart-container { margin: 40px 0; page-break-inside: avoid; }
        .chart-container img { width: 100%; height: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
        .info-box {
            background: #f7fafc;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 30px 0;
            border-radius: 8px;
        }
        .footer {
            margin-top: 60px;
            padding-top: 30px;
            border-top: 2px solid #e2e8f0;
            text-align: center;
            color: #718096;
            font-size: 0.9em;
        }
        @media print {
            body { padding: 20px; }
            .metric-card { break-inside: avoid; }
            .chart-container { break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🫁 Hypoxic Burden Analysis Report</h1>
        <p style="color: #718096; font-size: 1.1em;">Generated on ${date}</p>
    </div>

    <div class="info-box">
        <h3 style="margin-top: 0; color: #2d3748;">About Hypoxic Burden</h3>
        <p><strong>Hypoxic Burden (HB)</strong> quantifies the cumulative oxygen desaturation load during sleep by integrating
        both the depth and duration of SpO₂ drops. This metric has proven to be a stronger predictor of cardiovascular
        outcomes than traditional metrics (Azarbarzin et al., AJRCCM, 2019).</p>
        <p><strong>Methodology:</strong> Sutherland et al. (Sleep, 2022) - HB = Σ (desaturation area below baseline) / total sleep hours</p>
    </div>

    <h2>📊 Summary Metrics</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-label">Hypoxic Burden</div>
            <div class="metric-value">${(data.HB?.toFixed(3) || '--')}</div>
            <div class="metric-unit">%·min/hr</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Sleep Duration</div>
            <div class="metric-value">${(data.SleepHour?.toFixed(2) || '--')}</div>
            <div class="metric-unit">hours</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Events Detected</div>
            <div class="metric-value">${(data.events?.length || 0)}</div>
            <div class="metric-unit">apneas/hypopneas</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">SpO₂ Samples</div>
            <div class="metric-value">${(data.spo2?.length || 0)}</div>
            <div class="metric-unit">data points</div>
        </div>
    </div>

    <h2>📈 Visualizations</h2>
    <p style="color: #718096; font-style: italic; margin-bottom: 30px;">
        Note: For interactive charts with hover details, please use the web interface.
        To save these charts as images, right-click and select "Save image as..." from your browser.
    </p>

    <div class="chart-container">
        <h3>SpO₂ Time Series with Events</h3>
        ${spo2ChartDiv}
    </div>

    <div class="chart-container">
        <h3>Average SpO₂ Response Around Events</h3>
        ${avgChartDiv}
    </div>

    <div class="footer">
        <p><strong>Hypoxic Burden Calculator</strong> - Node.js Implementation</p>
        <p>Based on MATLAB reference by Sutherland et al. (Sleep, 2022)</p>
        <p>Contact: <a href="mailto:monetbrain@gmail.com">monetbrain@gmail.com</a></p>
        <p>&copy; ${new Date().getFullYear()} - For research and clinical use</p>
    </div>

    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
        // Example data for demonstration
        const resultData = ${JSON.stringify(data)};
        
        // Wait for Plotly to load, then render charts
        window.addEventListener('load', () => {
            setTimeout(() => {
                try {
                    renderChart1(resultData);
                    renderChart2(resultData);
                } catch (error) {
                    console.error('Error rendering charts:', error);
                    document.getElementById('chart1').innerHTML = '<p>Error loading chart: ' + error.message + '</p>';
                    document.getElementById('chart2').innerHTML = '<p>Error loading chart: ' + error.message + '</p>';
                }
            }, 100);
        });

        function renderChart1(data) {
            // Create time array from spo2 data length (assuming 1-second intervals)
            const t_hours = Array.from({length: data.spo2.length}, (_, i) => i / 3600);
            const traces = [{
                x: t_hours,
                y: data.spo2,
                type: 'scatter',
                mode: 'lines',
                name: 'SpO₂',
                line: { color: '#3b82f6', width: 1.5 },
                yaxis: 'y1'
            }];

            // Add hypnogram trace if sleep data is available
            if (data.sleep_a && data.sleep_a.length > 0 && data.sleep_t && data.sleep_t.length > 0) {
                // Convert sleep stage annotations to numeric values for plotting
                const stageToNumber = {
                    'Wake': 6, 'Stage 1': 1, 'Stage 2': 2, 'Stage 3': 3, 'Stage 4': 4, 'REM': 5, 'Indeterminant': 0
                };
                
                const hypnogramValues = data.sleep_a.map(stage => stageToNumber[stage] || 0);
                const hypnogramTimes = data.sleep_t.map(t => t / 3600); // Convert to hours
                
                traces.push({
                    x: hypnogramTimes,
                    y: hypnogramValues,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Sleep Stage',
                    line: { color: '#10b981', width: 2 },
                    yaxis: 'y2',
                    showlegend: true
                });
            }

            const shapes = [];
            if (data.events) {
                data.events.forEach(e => {
                    const startHours = e.Start / 3600;
                    const endHours = (e.Start + e.Duration) / 3600;
                    shapes.push({
                        type: 'line',
                        x0: startHours, x1: startHours,
                        y0: 0, y1: 1, yref: 'paper',
                        line: { color: 'rgba(239, 68, 68, 0.3)', width: 1, dash: 'dot' }
                    });
                    shapes.push({
                        type: 'line',
                        x0: endHours, x1: endHours,
                        y0: 0, y1: 1, yref: 'paper',
                        line: { color: 'rgba(239, 68, 68, 0.3)', width: 1, dash: 'dot' }
                    });
                });

                const apneas = data.events.filter(e => e.Type === 'Apnea');
                const hypopneas = data.events.filter(e => e.Type === 'Hypopnea');
                const desats = data.events.filter(e => e.Type === 'Desaturation');

                if (apneas.length > 0) {
                    traces.push({
                        x: apneas.map(e => e.Start / 3600),
                        y: apneas.map(() => 75),
                        type: 'scatter', mode: 'markers',
                        name: 'Apnea',
                        marker: { size: 8, color: '#ef4444', symbol: 'triangle-down' }
                    });
                }
                if (hypopneas.length > 0) {
                    traces.push({
                        x: hypopneas.map(e => e.Start / 3600),
                        y: hypopneas.map(() => 77),
                        type: 'scatter', mode: 'markers',
                        name: 'Hypopnea',
                        marker: { size: 8, color: '#f59e0b', symbol: 'circle' }
                    });
                }
                if (desats.length > 0) {
                    traces.push({
                        x: desats.map(e => e.Start / 3600),
                        y: desats.map(() => 79),
                        type: 'scatter', mode: 'markers',
                        name: 'Desaturation',
                        marker: { size: 8, color: '#06b6d4', symbol: 'square' }
                    });
                }
            }

            const layout = {
                title: 'SpO₂ Time Series with Sleep Events',
                xaxis: { title: 'Time (hours)' },
                yaxis: { 
                    title: 'SpO₂ (%)',
                    side: 'left'
                },
                yaxis2: {
                    title: 'Sleep Stage',
                    overlaying: 'y',
                    side: 'right',
                    tickvals: [0, 1, 2, 3, 4, 5, 6],
                    ticktext: ['Indet', 'N1', 'N2', 'N3', 'N4', 'REM', 'Wake'],
                    range: [-0.5, 6.5]
                },
                shapes: shapes,
                showlegend: true,
                legend: { orientation: 'h', yanchor: 'top', y: -0.15, xanchor: 'center', x: 0.5 },
                height: 500
            };

            Plotly.newPlot('chart1', traces, layout, { responsive: true });
        }

        function renderChart2(data) {
            if (!data.avg || data.avg.length === 0) return;

            const duravg = data.duravg || 34;
            const winstart = data.winstart || -34;
            const winfinish = data.winfinish || 90;
            const hbWinStart = data.HBWinStart || -5;
            const hbWinFinish = data.HBWinFinish || 45;
            const nadirx = data.nadirx || 0;
            const nadiry = data.nadiry || 0;
            const baselineOffset = -10;

            const n = data.avg.length;
            const xStart = winstart + duravg + baselineOffset;
            const x = Array.from({length: n}, (_, i) => xStart + i);

            // Safe index calculation with bounds checking
            const eventStartIdx = Math.max(0, Math.min(n - 1, Math.round(0 - xStart)));
            const eventEndIdx = Math.max(0, Math.min(n - 1, Math.round(duravg - xStart)));
            const winFinishIdx = n - 1;

            // Safe array access function
            const getSafeValue = (arr, idx) => arr[Math.max(0, Math.min(arr.length - 1, idx))];

            const traces = [
                {
                    x: x, y: data.avg,
                    type: 'scatter', mode: 'lines',
                    name: 'Average SpO₂',
                    line: { color: '#3b82f6', width: 2 }
                },
                {
                    x: x, y: data.filt,
                    type: 'scatter', mode: 'lines',
                    name: 'Filtered (12-pt MA)',
                    line: { color: '#10b981', width: 2.5 }
                },
                {
                    x: [x[0]], y: [getSafeValue(data.filt, 0)],
                    type: 'scatter', mode: 'markers',
                    name: 'Baseline',
                    marker: { size: 10, color: '#6b7280', symbol: 'circle' }
                },
                {
                    x: [0], y: [getSafeValue(data.filt, eventStartIdx)],
                    type: 'scatter', mode: 'markers',
                    name: 'Event Start',
                    marker: { size: 12, color: '#10b981', symbol: 'triangle-up' }
                },
                {
                    x: [nadirx], y: [nadiry],
                    type: 'scatter', mode: 'markers',
                    name: 'Nadir',
                    marker: { size: 12, color: '#3b82f6', symbol: 'triangle-down' }
                },
                {
                    x: [duravg], y: [getSafeValue(data.filt, eventEndIdx)],
                    type: 'scatter', mode: 'markers',
                    name: 'Event End',
                    marker: { size: 12, color: '#ef4444', symbol: 'triangle-down' }
                },
                {
                    x: [x[winFinishIdx]], y: [getSafeValue(data.filt, winFinishIdx)],
                    type: 'scatter', mode: 'markers',
                    name: 'WinFinish',
                    marker: { size: 12, color: '#8b5cf6', symbol: 'triangle-up' }
                }
            ];

            const shapes = [
                { type: 'line', x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper',
                  line: { color: 'rgba(16, 185, 129, 0.6)', width: 2, dash: 'dash' } },
                { type: 'line', x0: duravg, x1: duravg, y0: 0, y1: 1, yref: 'paper',
                  line: { color: 'rgba(107, 114, 128, 0.4)', width: 2, dash: 'dot' } },
                { type: 'line', x0: hbWinStart + duravg, x1: hbWinStart + duravg, y0: 0, y1: 1, yref: 'paper',
                  line: { color: 'rgba(132, 204, 22, 0.6)', width: 2, dash: 'dash' } },
                { type: 'line', x0: hbWinFinish + duravg, x1: hbWinFinish + duravg, y0: 0, y1: 1, yref: 'paper',
                  line: { color: 'rgba(217, 70, 239, 0.6)', width: 2, dash: 'dash' } }
            ];

            // Safe y-axis range calculation
            const validAvg = data.avg.filter(v => Number.isFinite(v) && !isNaN(v));
            const yMin = validAvg.length > 0 ? Math.min(...validAvg) : 90;
            const yMax = validAvg.length > 0 ? Math.max(...validAvg) : 100;

            const layout = {
                title: 'Average SpO₂ Response Around Events (n=' + (data.events?.length || 0) + ' events)',
                xaxis: { 
                    title: 'Time from Event Start (seconds)',
                    zeroline: true, zerolinecolor: '#000', zerolinewidth: 2
                },
                yaxis: { 
                    title: 'SpO₂ (%)',
                    range: [yMin - 2, yMax + 2]
                },
                shapes: shapes,
                showlegend: true,
                height: 500
            };

            Plotly.newPlot('chart2', traces, layout, { responsive: true });
        }
    </script>
</body>
</html>`;
}

// Start server
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║  Hypoxic Burden API Server (Node.js)                       ║
║  Running on: http://localhost:${PORT}                       ║
║  Visualization: http://localhost:${PORT}/visualize          ║
║  API Endpoint: POST /api/hb                                ║
║  Status: Ready ✓                                           ║
╚════════════════════════════════════════════════════════════╝
  `);
});

export default app;
