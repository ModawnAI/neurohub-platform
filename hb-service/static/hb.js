const STAGE_DESCRIPTIONS = [
  "Wake",
  "Stage 1",
  "Stage 2",
  "Stage 3",
  "Stage 4",
  "REM",
  "Indeterminant"
];

const STAGE_LOOKUP = {
  W: "Wake",
  WAKE: "Wake",
  "STAGE W": "Wake",
  N1: "Stage 1",
  "STAGE 1": "Stage 1",
  "NREM1": "Stage 1",
  "NREM 1": "Stage 1",
  N2: "Stage 2",
  "STAGE 2": "Stage 2",
  "NREM2": "Stage 2",
  "NREM 2": "Stage 2",
  N3: "Stage 3",
  N4: "Stage 4",
  "STAGE 3": "Stage 3",
  "STAGE 4": "Stage 4",
  "SWS": "Stage 3",
  R: "REM",
  REM: "REM",
  "?": "Indeterminant",
  N: "Indeterminant",
  U: "Indeterminant",
  UNDEFINED: "Indeterminant",
  UNKNOWN: "Indeterminant",
  ARTIFACT: "Indeterminant"
};

async function uploadAndCalc() {
  const spo2File = document.getElementById("spo2")?.files?.[0];
  const hypnFile = document.getElementById("hypn")?.files?.[0];
  const eventFile = document.getElementById("eventlist")?.files?.[0];

  if (!spo2File || !hypnFile || !eventFile) {
    alert("Please upload all three files.");
    return;
  }

  const infoEl = document.getElementById("info");
  const button = document.getElementById("runHB");
  if (button) button.disabled = true;

  try {
    if (infoEl) infoEl.innerHTML = "<p>Processing files…</p>";

    const payload = await computeHypoxicBurden(spo2File, hypnFile, eventFile);

    const hbText = Number.isFinite(payload.HB)
      ? `${payload.HB.toFixed(3)} %·min/hr`
      : "Unavailable";
    const sleepText = Number.isFinite(payload.SleepHour)
      ? `${payload.SleepHour.toFixed(2)} hr`
      : "Unavailable";
    const showAhiOption = typeof document !== 'undefined' ? (document.getElementById('showAhi')?.checked ?? true) : true;
    const ahiText = Number.isFinite(payload.AHI)
      ? `${payload.AHI.toFixed(2)} events/hr`
      : (Number.isFinite(payload.SleepHour) && payload.SleepHour > 0 ? `${(payload.events.length / payload.SleepHour).toFixed(2)} events/hr` : "Unavailable");

    if (infoEl) {
      infoEl.innerHTML = `
        <h3>Hypoxic Burden: ${hbText}</h3>
        <p>Sleep hours: ${sleepText}</p>
        <p>Respiratory events analysed: ${payload.events.length}</p>
        ` + (showAhiOption ? `<p>AHI: ${ahiText}</p>` : ``) + `
      `;
    }

    drawSpO2Plot(payload);
    drawHBWaveform(payload);

    const linksEl = document.getElementById("links");
    if (linksEl) linksEl.innerHTML = "";
  } catch (err) {
    console.error(err);
    alert(`Failed to compute hypoxic burden: ${err.message || err}`);
    if (infoEl) infoEl.innerHTML = "<p class=\"text-danger\">Computation failed.</p>";
  } finally {
    if (button) button.disabled = false;
  }
}

async function computeHypoxicBurden(spo2File, hypnFile, eventFile) {
  const [spo2Text, hypnText, eventText] = await Promise.all([
    spo2File.text(),
    hypnFile.text(),
    eventFile.text()
  ]);

  const spo2Rows = parseDelimited(spo2Text).rows;
  const hypnRows = parseDelimited(hypnText).rows;
  const eventRows = parseEventList(eventText);

  const spo2 = buildSpO2Series(spo2Rows);
  const sleepStage = buildSleepStage(hypnRows, spo2.absoluteTimes[0]);
  const events = alignEvents(eventRows, spo2.absoluteTimes[0]);

  if (!events.length) {
    throw new Error("No apnea/hypopnea/desaturation events found in the event list.");
  }

  const { HB, result } = calcHBCore(spo2.values, 1, events, sleepStage);

  const shift = Math.floor((result.SpO2avg || []).length / 2);
  const sleepHour = result.SleepHour;
  const ahi = Number.isFinite(sleepHour) && sleepHour > 0 ? (events.length / sleepHour) : NaN;

  return {
    HB,
    AHI: ahi,
    SleepHour: sleepHour,
    t: safeFloatList(spo2.tSec),
    spo2: safeFloatList(spo2.values),
    sleep_t: safeFloatList(sleepStage.t),
    sleep_a: safeFloatList(sleepStage.Annotation),
    codes: sleepStage.Codes.slice(),
    desc: sleepStage.Description.slice(),
    events: events.map(ev => ({
      ...ev,
      Start: ev.Start,
      Duration: ev.Duration,
      Type: ev.Type
    })),
    avg: safeFloatList(result.SpO2avg),
    filt: safeFloatList(result.SpO2avgfilt),
    std: safeFloatList(result.SpO2std),
    duravg: result.DurAvg,
    winstart: result.WinStart + shift,
    winfinish: result.WinFinish + shift,
    nadirx: (result.NadirIdx ?? 0) + shift,
    nadiry: result.Nadir,
    pdf_url: "",
    xlsx_url: ""
  };
}

function parseDelimited(text) {
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");

  let delimiter = ",";
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.includes("\t")) {
      delimiter = "\t";
      break;
    }
    if (trimmed.includes(",")) {
      delimiter = ",";
      break;
    }
    if (trimmed.includes(";")) {
      delimiter = ";";
      break;
    }
  }

  const rows = [];
  for (const line of lines) {
    const raw = line.trimEnd();
    if (!raw) continue;
    rows.push(parseDelimitedLine(raw, delimiter));
  }
  return { delimiter, rows };
}

function parseDelimitedLine(line, delimiter) {
  if (delimiter === "\t") {
    return line.split("\t").map(cell => cell.trim());
  }

  if (delimiter === ";") {
    return line.split(";").map(cell => cell.trim());
  }

  const out = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === "\"") {
      if (inQuotes && line[i + 1] === "\"") {
        current += "\"";
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === delimiter && !inQuotes) {
      out.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  out.push(current.trim());
  return out;
}

function parseEventList(text) {
  const sanitized = text
    .replace(/\x00/g, "")
    .split(/\r?\n/)
    .map(line => line.replace(/[\u200b\u200e\u200f\ufeff]/g, "").trim());

  const headerIdx = sanitized.findIndex(line => /\btime\b/i.test(line));
  if (headerIdx === -1) {
    throw new Error("Cannot find header line with 'Time' in event list.");
  }

  const headerLine = sanitized[headerIdx];
  const delimiter = headerLine.includes("\t")
    ? "\t"
    : headerLine.includes(",")
      ? ","
      : null;

  const header = delimiter
    ? parseDelimitedLine(headerLine, delimiter)
    : splitByWhitespace(headerLine);

  const normalizedHeader = header.map(h =>
    h.replace(/[^\w\d]+/g, "").trim()
  );

  const rows = [];
  for (let i = headerIdx + 1; i < sanitized.length; i++) {
    const line = sanitized[i];
    if (!line) continue;
    const cols = delimiter
      ? parseDelimitedLine(line, delimiter)
      : splitByWhitespace(line);
    if (!cols.length) continue;
    rows.push(cols);
  }

  const events = [];
  for (const row of rows) {
    const record = {};
    normalizedHeader.forEach((key, idx) => {
      record[key || `COL${idx}`] = row[idx] ?? "";
    });

    const titleRaw = String(record.Title || record.Event || "").trim();
    if (!titleRaw) continue;

    if (!/(apnea|hypopnea|desaturation)/i.test(titleRaw)) continue;

    const start = parseTimeValue(record.Time || record.Start || record.StartTime);
    let duration = parseDurationValue(record.Duration || record.Length || "");

    if (!Number.isFinite(start)) continue;
    if (!Number.isFinite(duration) || duration <= 0) duration = 10;

    let type = "Other";
    if (/apnea/i.test(titleRaw)) type = "Apnea";
    else if (/hypopnea/i.test(titleRaw)) type = "Hypopnea";
    else if (/desaturation/i.test(titleRaw)) type = "Desaturation";

    events.push({
      Start: start,
      Duration: duration,
      Type: type,
      Title: titleRaw
    });
  }

  return events;
}

function splitByWhitespace(line) {
  return line
    .split(/\s{2,}|\t+/)
    .map(cell => cell.trim())
    .filter(Boolean);
}

function buildSpO2Series(rows) {
  const filtered = rows.filter(row => row.some(cell => (cell ?? "").toString().trim() !== ""));
  if (!filtered.length) throw new Error("SpO₂ file appears to be empty.");

  const dataRows = filtered.map(row => row.slice());
  const timeIdx = pickTimeColumn(dataRows);
  const valueIdx = pickValueColumn(dataRows, timeIdx);

  const points = [];
  for (const row of dataRows) {
    const tAbs = parseTimeValue(row[timeIdx]);
    const value = parseNumber(row[valueIdx]);
    if (!Number.isFinite(tAbs) || !Number.isFinite(value)) continue;
    points.push({ tAbs, value });
  }

  if (!points.length) {
    throw new Error("Failed to parse usable SpO₂ samples.");
  }

  points.sort((a, b) => a.tAbs - b.tAbs);

  const times = points.map(p => p.tAbs);
  const corrected = correctDayRollover(times);
  const t0 = corrected[0];
  const tSec = corrected.map(t => t - t0);

  const values = points.map(p => p.value);
  const mean = nanMean(values);
  const scaledValues = mean < 5 ? values.map(v => v * 100) : values.slice();

  return {
    values: scaledValues,
    tSec,
    absoluteTimes: corrected
  };
}

function pickTimeColumn(rows) {
  const nCols = rows.reduce((max, row) => Math.max(max, row.length), 0);
  let bestIdx = 0;
  let bestScore = -Infinity;

  for (let col = 0; col < nCols; col++) {
    let valid = 0;
    let colonBonus = 0;
    for (const row of rows) {
      const cell = row[col];
      const value = parseTimeValue(cell);
      if (Number.isFinite(value)) valid += 1;
      if (cell && String(cell).includes(":")) colonBonus += 0.2;
    }
    const score = valid + colonBonus;
    if (score > bestScore) {
      bestScore = score;
      bestIdx = col;
    }
  }

  return bestIdx;
}

function pickValueColumn(rows, timeIdx) {
  const nCols = rows.reduce((max, row) => Math.max(max, row.length), 0);
  let bestIdx = -1;
  let bestScore = -Infinity;

  for (let col = 0; col < nCols; col++) {
    if (col === timeIdx) continue;
    let valid = 0;
    for (const row of rows) {
      const num = parseNumber(row[col]);
      if (Number.isFinite(num)) valid += 1;
    }
    if (valid > bestScore) {
      bestScore = valid;
      bestIdx = col;
    }
  }

  if (bestIdx === -1) {
    throw new Error("Unable to identify SpO₂ value column.");
  }
  return bestIdx;
}

function buildSleepStage(rows, referenceStart) {
  const filtered = rows.filter(row => row.some(cell => (cell ?? "").toString().trim() !== ""));
  if (!filtered.length) throw new Error("Hypnogram file appears to be empty.");

  const dataRows = filtered.map(row => row.slice());
  const timeIdx = pickTimeColumn(dataRows);
  const stageIdx = pickStageColumn(dataRows, timeIdx);

  const entries = [];
  for (const row of dataRows) {
    const tAbs = parseTimeValue(row[timeIdx]);
    const stage = normalizeStage(row[stageIdx]);
    if (!Number.isFinite(tAbs)) continue;
    entries.push({ tAbs, stage });
  }

  if (!entries.length) {
    throw new Error("Failed to parse hypnogram timestamps.");
  }

  entries.sort((a, b) => a.tAbs - b.tAbs);

  const times = entries.map(e => e.tAbs);
  const corrected = correctDayRollover(times);
  const base = referenceStart ?? corrected[0];
  const tSec = corrected.map(t => t - base);
  const annotations = entries.map(e => STAGE_DESCRIPTIONS.indexOf(e.stage));

  return {
    t: tSec,
    Annotation: annotations,
    Codes: STAGE_DESCRIPTIONS.map((_, idx) => idx),
    Description: STAGE_DESCRIPTIONS.slice(),
    SR: 1
  };
}

function pickStageColumn(rows, timeIdx) {
  const nCols = rows.reduce((max, row) => Math.max(max, row.length), 0);
  let bestIdx = -1;
  let bestScore = -Infinity;

  for (let col = 0; col < nCols; col++) {
    if (col === timeIdx) continue;
    let score = 0;
    for (const row of rows) {
      const stage = normalizeStage(row[col]);
      if (stage !== "Indeterminant") score += 1;
    }
    if (score > bestScore) {
      bestScore = score;
      bestIdx = col;
    }
  }

  if (bestIdx === -1) {
    bestIdx = timeIdx === 0 ? 1 : timeIdx - 1;
  }
  return Math.max(0, bestIdx);
}

function normalizeStage(value) {
  if (value == null) return "Indeterminant";
  let str = String(value).trim();
  if (!str) return "Indeterminant";
  str = str.replace(/"/g, "");
  const upper = str.toUpperCase();

  if (STAGE_LOOKUP[upper]) return STAGE_LOOKUP[upper];

  const simplified = upper.replace(/\s+/g, "");
  if (STAGE_LOOKUP[simplified]) return STAGE_LOOKUP[simplified];

  const directMatch = STAGE_DESCRIPTIONS.find(desc => desc.toUpperCase() === upper);
  return directMatch || "Indeterminant";
}

function alignEvents(events, referenceStart) {
  if (!events.length) return [];

  const starts = events.map(ev => ev.Start);
  const corrected = correctDayRollover(starts);

  return events
    .map((ev, idx) => {
      const start = corrected[idx] - referenceStart;
      const duration = Number.isFinite(ev.Duration) && ev.Duration > 0 ? ev.Duration : 10;
      return {
        Start: start,
        Duration: duration,
        Type: ev.Type,
        Title: ev.Title
      };
    })
    .filter(ev => Number.isFinite(ev.Start) && ev.Start >= 0)
    .sort((a, b) => a.Start - b.Start);
}

function calcHBCore(o2, fs, respEvents, sleepStage) {
  const cleaned = o2.map(v => {
    const num = Number(v);
    if (!Number.isFinite(num)) return NaN;
    if (num < 50 || num > 100) return NaN;
    return num;
  });

  if (!respEvents.length) {
    return {
      HB: NaN,
      result: {
        HB: NaN,
        SpO2avg: [],
        SpO2avgfilt: [],
        SpO2std: [],
        NadirIdx: null,
        Nadir: NaN,
        WinStart: -5,
        WinFinish: 45,
        DurAvg: 0,
        AvgGap: 0,
        SleepHour: 0
      }
    };
  }

  const starts = respEvents.map(ev => Number(ev.Start));
  const durations = respEvents.map(ev => Number(ev.Duration));
  const ends = starts.map((s, idx) => Math.round(s + durations[idx]));
  const N = cleaned.length;

  const validDur = durations.filter(d => Number.isFinite(d) && d > 0);
  const DurAvg = validDur.length
    ? Math.round(validDur.reduce((a, b) => a + b, 0) / validDur.length)
    : 0;

  const gaps = [];
  for (let i = 1; i < starts.length; i++) {
    const gap = starts[i] - starts[i - 1];
    if (Number.isFinite(gap)) gaps.push(gap);
  }
  const AvgGap = gaps.length
    ? Math.round(gaps.reduce((a, b) => a + b, 0) / gaps.length)
    : 30;

  const winPre = 120;
  const winPost = 120;
  const totalLen = Math.round((winPre + winPost) * fs) + 1;
  const mid = Math.round(winPre * fs);

  const SpO2Events = Array.from({ length: totalLen }, () =>
    Array(respEvents.length).fill(NaN)
  );

  for (let i = 0; i < ends.length; i++) {
    const end = Math.round(ends[i]);
    const lo = end - mid;
    const hi = end + Math.round(winPost * fs);

    if (lo >= 0 && hi < N) {
      const segment = cleaned.slice(lo, hi + 1);
      for (let j = 0; j < totalLen && j < segment.length; j++) {
        SpO2Events[j][i] = segment[j];
      }
    }
  }

  const SpO2avg = SpO2Events.map(col => nanMean(col));
  const SpO2std = SpO2Events.map(col => nanStd(col));
  const kernelSize = Math.max(1, Math.round(30 * fs));
  const kernel = Array.from({ length: kernelSize }, () => 1 / kernelSize);
  const SpO2avgFiltFull = convolveSame(SpO2avg, kernel);

  const s = mid - Math.round(DurAvg * fs);
  const f = mid + Math.round(Math.min(90, AvgGap) * fs);
  const sliceStart = Math.max(0, s);
  const sliceEnd = Math.min(totalLen, f);

  const avgSlice = SpO2avg.slice(sliceStart, sliceEnd);
  const filtSlice = SpO2avgFiltFull.slice(sliceStart, sliceEnd);
  const stdSlice = SpO2std.slice(sliceStart, sliceEnd);

  const NadirIdx = nanArgMin(filtSlice);
  const Nadir = NadirIdx !== null ? filtSlice[NadirIdx] : NaN;

  const WinStart = -5;
  const WinFinish = 45;

  let percentMins = 0;
  let limit = 0;
  for (let i = 0; i < ends.length; i++) {
    const end = Math.round(ends[i]);
    if (end > 100 && end + WinFinish < N) {
      const preSlice = cleaned.slice(end - 100, end).filter(Number.isFinite);
      const pre = preSlice.length ? Math.max(...preSlice) : NaN;
      const segStart = Math.max(Math.round(end + WinStart), limit, 0);
      const segEnd = Math.min(Math.round(end + WinFinish), N);

      let area = 0;
      if (Number.isFinite(pre)) {
        for (let idx = segStart; idx < segEnd; idx++) {
          const val = cleaned[idx];
          if (!Number.isFinite(val)) continue;
          const diff = pre - val;
          if (diff > 0) area += diff;
        }
      }
      percentMins += area / (60 * fs);
      limit = segEnd;
    }
  }

  const ann = sleepStage.Annotation.slice(
    0,
    Math.min(sleepStage.Annotation.length, cleaned.length)
  );
  const truncatedO2 = cleaned.slice(0, ann.length);

  let validSamples = 0;
  for (let i = 0; i < ann.length; i++) {
    if (ann[i] > 0 && ann[i] < 9 && Number.isFinite(truncatedO2[i])) {
      validSamples += 1;
    }
  }

  const sleepHours = validSamples / (3600 * (sleepStage.SR || 1));
  const HB = sleepHours > 0 ? percentMins / sleepHours : NaN;

  return {
    HB,
    result: {
      HB,
      SpO2avg: avgSlice,
      SpO2avgfilt: filtSlice,
      SpO2std: stdSlice,
      NadirIdx,
      Nadir,
      WinStart,
      WinFinish,
      DurAvg,
      AvgGap,
      SleepHour: sleepHours
    }
  };
}

function parseTimeValue(value) {
  if (value == null) return NaN;
  const str = String(value).trim();
  if (!str) return NaN;

  const parsedDate = Date.parse(str);
  if (!Number.isNaN(parsedDate)) {
    return parsedDate / 1000;
  }

  if (/^-?\d+(\.\d+)?$/.test(str)) {
    return Number.parseFloat(str);
  }

  const parts = str.split(":");
  if (parts.length > 1) {
    let seconds = 0;
    let factor = 1;
    for (let i = parts.length - 1; i >= 0; i--) {
      const segment = parts[i].trim();
      if (segment === "") return NaN;
      const num = Number.parseFloat(segment);
      if (!Number.isFinite(num)) return NaN;
      seconds += num * factor;
      factor *= 60;
    }
    return seconds;
  }

  const num = Number.parseFloat(str);
  return Number.isFinite(num) ? num : NaN;
}

function parseDurationValue(value) {
  if (value == null) return NaN;
  const str = String(value).trim();
  if (!str) return NaN;
  if (/^-?\d+(\.\d+)?$/.test(str)) return Number.parseFloat(str);
  return parseTimeValue(str);
}

function parseNumber(value) {
  if (value == null) return NaN;
  const str = String(value).trim();
  if (!str) return NaN;
  const cleaned = str.replace(/[^0-9+-.eE]/g, "");
  if (!cleaned) return NaN;
  const num = Number.parseFloat(cleaned);
  return Number.isFinite(num) ? num : NaN;
}

function correctDayRollover(times) {
  const out = [];
  let wrap = 0;
  let last = null;

  for (const t of times) {
    if (!Number.isFinite(t)) {
      out.push(NaN);
      continue;
    }
    if (last !== null && t < last - 60) {
      wrap += 24 * 3600;
    }
    const adjusted = t + wrap;
    out.push(adjusted);
    last = t;
  }

  const valid = out.filter(Number.isFinite);
  if (valid.length) {
    const max = Math.max(...valid);
    const min = Math.min(...valid);
    const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
    if ((max - min) < 3600 && mean < 6 * 3600) {
      return out.map(v =>
        Number.isFinite(v) ? v + 24 * 3600 : v
      );
    }
  }
  return out;
}

function nanMean(arr) {
  const valid = arr.filter(Number.isFinite);
  if (!valid.length) return NaN;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

function nanStd(arr) {
  const valid = arr.filter(Number.isFinite);
  if (!valid.length) return NaN;
  const mean = nanMean(valid);
  const variance = valid.reduce((sum, val) => sum + (val - mean) ** 2, 0) / valid.length;
  return Math.sqrt(variance);
}

function convolveSame(signal, kernel) {
  const n = signal.length;
  const k = kernel.length;
  const half = Math.floor(k / 2);
  const output = new Array(n).fill(NaN);

  for (let i = 0; i < n; i++) {
    let acc = 0;
    let weight = 0;
    for (let j = 0; j < k; j++) {
      const idx = i + j - half;
      if (idx < 0 || idx >= n) continue;
      const val = signal[idx];
      if (!Number.isFinite(val)) continue;
      acc += val * kernel[j];
      weight += kernel[j];
    }
    output[i] = weight > 0 ? acc / weight : NaN;
  }

  return output;
}

function nanArgMin(arr) {
  let bestIdx = null;
  let bestVal = Infinity;
  arr.forEach((val, idx) => {
    if (Number.isFinite(val) && val < bestVal) {
      bestVal = val;
      bestIdx = idx;
    }
  });
  return bestIdx;
}

function safeFloatList(arr) {
  if (!Array.isArray(arr)) return [];
  return arr.map(v => {
    const num = Number(v);
    if (!Number.isFinite(num)) return 0;
    return num;
  });
}

function drawSpO2Plot(data) {
  const t_hr = data.t.map(t => t / 3600);

  const spo2Trace = {
    x: t_hr,
    y: data.spo2,
    mode: 'lines',
    name: 'SpO₂ (%)',
    line: { color: 'blue', width: 1.3 },
    yaxis: 'y1'
  };

  const stageTrace = {
    x: data.sleep_t.map(t => t / 3600),
    y: data.sleep_a,
    mode: 'lines',
    name: 'Sleep Stage',
    line: { color: 'black', width: 1 },
    yaxis: 'y2'
  };

  // Shapes for events
  const eventShapes = (data.events || []).map(e => ({
    type: 'line',
    x0: e.Start / 3600,
    x1: e.Start / 3600,
    y0: 0,
    y1: 1,
    xref: 'x',
    yref: 'paper',
    line: {
      color: e.Type.toLowerCase().includes('apnea') ? 'crimson'
            : e.Type.toLowerCase().includes('hypopnea') ? 'darkorange'
            : 'gray',
      width: 1,
      dash: 'dot'
    }
  }));

  // Dummy traces for legend
  const apneaLegend = {
    x: [null], y: [null],
    mode: 'lines',
    name: 'Apnea',
    line: { color: 'crimson', dash: 'dot', width: 2 },
    showlegend: true
  };

  const hypopneaLegend = {
    x: [null], y: [null],
    mode: 'lines',
    name: 'Hypopnea',
    line: { color: 'darkorange', dash: 'dot', width: 2 },
    showlegend: true
  };

  const layout = {
    title: 'SpO₂ Trace with Sleep Stages & Events',
    height: 500,
    xaxis: { title: 'Time (hours)' },
    yaxis: {
      title: 'SpO₂ (%)',
      range: [80, 100],
      showgrid: true,
      zeroline: false
    },
    yaxis2: {
      title: 'Sleep Stage',
      overlaying: 'y',
      side: 'right',
      tickvals: data.codes,
      ticktext: data.desc
    },
    legend: { orientation: 'h', x: 0.5, y: -0.25, xanchor: 'center' },
    shapes: eventShapes,
    margin: { t: 50, l: 60, r: 60, b: 50 }
  };

  Plotly.newPlot('plot',
    [spo2Trace, stageTrace, apneaLegend, hypopneaLegend],
    layout
  );
}


function drawHBWaveform(data) {
  if (!data.avg || data.avg.length === 0) return;

  // Relative time axis (centered on event end)
  const shift = Math.floor(data.avg.length / 2);
  const t_rel = Array.from({ length: data.avg.length }, (_, i) => i - shift);

  const sdUpper = data.avg.map((v, i) => v + (data.std?.[i] || 0));
  const sdLower = data.avg.map((v, i) => v - (data.std?.[i] || 0));

  // ±SD shaded band
  const sdBand = {
    x: [...t_rel, ...t_rel.slice().reverse()],
    y: [...sdUpper, ...sdLower.slice().reverse()],
    fill: 'toself',
    fillcolor: 'rgba(173,216,230,0.3)',
    line: { width: 0 },
    name: '±SD',
    showlegend: true
  };

  // Mean and filtered traces
  const meanTrace = {
    x: t_rel,
    y: data.avg,
    mode: 'lines',
    name: 'Mean',
    line: { color: 'black', dash: 'dot', width: 1.5 }
  };

  const filtTrace = {
    x: t_rel,
    y: data.filt,
    mode: 'lines',
    name: 'Filtered Mean',
    line: { color: 'red', width: 2 }
  };

  // --- Nadir point marker ---
  const nadirPoint = (data.nadirx !== undefined && data.nadiry !== undefined)
    ? [{
        x: [data.nadirx - shift],  // convert to relative coordinate
        y: [data.nadiry],
        mode: 'markers+text',
        text: ['Nadir'],
        textposition: 'bottom right',
        marker: { color: 'blue', size: 10, symbol: 'triangle-down' },
        name: 'Nadir Point'
      }]
    : [];

  // --- Vertical markers (WinStart / WinFinish / DurAvg / Nadir line) ---
  const shapes = [];

  if (data.winstart !== undefined)
    shapes.push({
      type: 'line',
      x0: data.winstart - shift, x1: data.winstart - shift,
      yref: 'paper', y0: 0, y1: 1,
      line: { color: 'limegreen', width: 2, dash: 'dash' }
    });

  if (data.winfinish !== undefined)
    shapes.push({
      type: 'line',
      x0: data.winfinish - shift, x1: data.winfinish - shift,
      yref: 'paper', y0: 0, y1: 1,
      line: { color: 'magenta', width: 2, dash: 'dash' }
    });

  if (data.duravg !== undefined)
    shapes.push({
      type: 'line',
      x0: data.duravg - shift, x1: data.duravg - shift,
      yref: 'paper', y0: 0, y1: 1,
      line: { color: 'gray', width: 2, dash: 'dot' }
    });

  if (data.nadirx !== undefined)
    shapes.push({
      type: 'line',
      x0: data.nadirx - shift, x1: data.nadirx - shift,
      yref: 'paper', y0: 0, y1: 1,
      line: { color: 'blue', width: 2, dash: 'dot' }
    });

  // --- Layout ---
  const ymin = Math.min(...sdLower, data.nadiry || 100) - 1;
  const ymax = Math.max(...sdUpper, 100) + 1;

  const layout = {
    title: 'Average Desaturation Waveform',
    xaxis: { title: 'Time (samples, relative to event end)' },
    yaxis: { title: 'SpO₂ (%)', range: [ymin, ymax] },
    shapes: shapes,
    height: 400,
    legend: { orientation: 'h', x: 0.5, y: -0.25, xanchor: 'center' }
  };

  Plotly.newPlot('wave', [sdBand, meanTrace, filtTrace, ...nadirPoint], layout);
}


window.uploadAndCalc = uploadAndCalc;
