/**
 * Server-side Hypoxic Burden Calculator
 * Extracted from hb.js for Node.js backend processing
 */

import fs from 'fs';
import path from 'path';

// ============================================================================
// Constants & Lookups
// ============================================================================

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

// ============================================================================
// File Reading & Parsing Utilities
// ============================================================================

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

// ============================================================================
// SpO2 & Sleep Stage Building
// ============================================================================

function buildSpO2Series(rows) {
  const filtered = rows.filter(row => row.some(cell => (cell ?? "").toString().trim() !== ""));
  if (!filtered.length) throw new Error("SpO₂ file appears to be empty.");

  // Skip header row
  let dataRows = filtered;
  if (dataRows.length > 0) {
    const firstRow = dataRows[0].map(cell => String(cell).toLowerCase());
    if (firstRow.some(cell => /position|time|spo2|osat|sat/.test(cell))) {
      dataRows = dataRows.slice(1);
    }
  }
  
  if (!dataRows.length) throw new Error("No data rows found in SpO₂ file.");

  // Column 1 is absolute time (MATLAB uses column 2 which is 1-indexed)
  const timeCol = 1; 
  const valueCol = 2;

  const points = [];
  for (const row of dataRows) {
    const tAbs = parseTimeValue(row[timeCol]);
    const value = parseNumber(row[valueCol]);
    if (!Number.isFinite(tAbs) || !Number.isFinite(value)) continue;
    points.push({ tAbs, value });
  }

  if (!points.length) {
    throw new Error("Failed to parse usable SpO₂ samples.");
  }

  // Extract absolute times and unwrap midnight rollover
  const absoluteTimes = points.map(p => p.tAbs);
  const unwrapped = correctDayRollover(absoluteTimes);
  
  // Normalize to t0 (first sample time)
  const t0 = unwrapped[0];
  const tSec = unwrapped.map(t => t - t0);
  const values = points.map(p => p.value);

  return {
    tSec,
    values,
    absoluteTimes: unwrapped,  // Return unwrapped absolute times for adjustDayShift
    t0,                         // Return t0 for normalization
    SR: 1
  };
}

function buildSleepStage(rows, spo2AbsTimes, t0) {
  const filtered = rows.filter(row => row.some(cell => (cell ?? "").toString().trim() !== ""));
  if (!filtered.length) {
    return {
      t: [],
      Annotation: [],
      Codes: [0, 1, 2, 3, 4, 5, 6],
      Description: STAGE_DESCRIPTIONS,
      SR: 1
    };
  }

  // Skip header row
  let dataRows = filtered;
  if (filtered.length > 0) {
    const firstRow = filtered[0].map(cell => String(cell).toLowerCase());
    if (firstRow.some(cell => /position|time|stage|epoch/.test(cell))) {
      dataRows = filtered.slice(1);
    }
  }
  
  if (!dataRows.length) {
    return {
      t: [],
      Annotation: [],
      Codes: [0, 1, 2, 3, 4, 5, 6],
      Description: STAGE_DESCRIPTIONS,
      SR: 1
    };
  }

  // Parse column 1 (absolute time HH:MM:SS) - NO sorting!
  const timeStrings = dataRows.map(row => row[1]);
  const rawTimes = timeStrings.map(parseTimeValue);
  
  // Unwrap midnight rollover
  const t_hypn = correctDayRollover(rawTimes);
  
  // Adjust day shift relative to SpO2
  const t_hypn_adjusted = adjustDayShift(t_hypn, spo2AbsTimes);
  
  // Normalize to t0
  const t_normalized = t_hypn_adjusted.map(t => t - t0);
  
  // Parse stages
  const stages = dataRows.map(row => normalizeStage(row[2]));
  const codes = stages.map(s => {
    const idx = STAGE_DESCRIPTIONS.indexOf(s);
    return idx !== -1 ? idx : 6;
  });

  return {
    t: t_normalized,
    Annotation: codes,
    Codes: [0, 1, 2, 3, 4, 5, 6],
    Description: STAGE_DESCRIPTIONS,
    SR: 1
  };
}

function pickTimeColumn(rows) {
  const nCols = rows.reduce((max, row) => Math.max(max, row.length), 0);
  const timeColumns = [];
  
  // Find all columns that look like time
  for (let col = 0; col < nCols; col++) {
    let score = 0;
    for (const row of rows) {
      const val = row[col];
      if (!val) continue;
      const str = String(val).trim();
      if (/^\d{1,2}:\d{2}/.test(str)) score += 10;
      else if (/^\d+(\.\d+)?$/.test(str)) {
        const num = Number.parseFloat(str);
        if (num >= 0 && num <= 86400) score += 5;
      }
    }
    if (score > 0) {
      timeColumns.push({ col, score });
    }
  }
  
  // If there are multiple time columns, prefer the second one (absolute time)
  // as the first is usually relative time starting from 00:00:00
  if (timeColumns.length >= 2) {
    // Sort by column index and pick the second one
    timeColumns.sort((a, b) => a.col - b.col);
    return timeColumns[1].col;
  }
  
  // Otherwise, pick the column with the highest score
  if (timeColumns.length > 0) {
    timeColumns.sort((a, b) => b.score - a.score);
    return timeColumns[0].col;
  }
  
  return 0;
}

function pickValueColumn(rows, timeIdx) {
  const nCols = rows.reduce((max, row) => Math.max(max, row.length), 0);
  let bestCol = -1;
  let bestScore = -Infinity;

  for (let col = 0; col < nCols; col++) {
    if (col === timeIdx) continue;
    let score = 0;
    for (const row of rows) {
      const num = parseNumber(row[col]);
      if (Number.isFinite(num) && num >= 50 && num <= 100) score += 1;
    }
    if (score > bestScore) {
      bestScore = score;
      bestCol = col;
    }
  }

  if (bestCol === -1) {
    bestCol = timeIdx === 0 ? 1 : timeIdx - 1;
  }
  return Math.max(0, bestCol);
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

// ============================================================================
// Event Alignment
// ============================================================================

function alignEvents(events, spo2AbsTimes, t0) {
  if (!events.length) return [];

  // Events already have Start in seconds - unwrap and adjust
  const starts = events.map(ev => ev.Start);
  const corrected = correctDayRollover(starts);
  const adjusted = adjustDayShift(corrected, spo2AbsTimes);

  return events
    .map((ev, idx) => {
      const start = adjusted[idx] - t0;
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

// ============================================================================
// Core HB Calculation
// ============================================================================

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
  
  // Simple moving average filter (window of 12 points: i-5 to i+6)
  const SpO2avgFiltFull = SpO2avg.map((_, i, a) => {
    const start = Math.max(0, i - 5);
    const end = Math.min(a.length, i + 6);
    return nanMean(a.slice(start, end));
  });

  const s = mid - Math.round(DurAvg * fs);
  const f = mid + Math.round(Math.min(90, AvgGap) * fs);
  const sliceStart = Math.max(0, s);
  const sliceEnd = Math.min(totalLen, f);

  const avgSlice = SpO2avg.slice(sliceStart, sliceEnd);
  const filtSlice = SpO2avgFiltFull.slice(sliceStart, sliceEnd);
  const stdSlice = SpO2std.slice(sliceStart, sliceEnd);

  const NadirIdx = nanArgMin(filtSlice);
  const Nadir = NadirIdx !== null ? filtSlice[NadirIdx] : NaN;

  // Calculate window range relative to event end for VISUALIZATION
  const WinStart = sliceStart - mid;  
  const WinFinish = sliceEnd - mid;   

  // For HB calculation, use MATLAB defaults: -5 to +45 seconds
  // (MATLAB tries to find optimal window but falls back to these defaults)
  const hbWinStart = -5;
  const hbWinFinish = 45;

  let percentMins = 0;
  let limit = 0;
  
  for (let i = 0; i < ends.length; i++) {
    const end = Math.round(ends[i]);
    if (end > 100 && end + hbWinFinish < N) {
      // Get baseline SpO2 (max in 100 seconds before event end)
      const preSlice = cleaned.slice(end - 100, end).filter(Number.isFinite);
      const pre = preSlice.length ? Math.max(...preSlice) : NaN;
      
      // Define analysis window: from (end + hbWinStart) to (end + hbWinFinish)
      // But don't overlap with previous event's window
      const segStart = Math.max(Math.round(end + hbWinStart), limit);
      const segEnd = Math.round(end + hbWinFinish);

      let area = 0;
      if (Number.isFinite(pre) && segStart < segEnd) {
        // Calculate area: sum of (baseline - SpO2) for all drops
        for (let idx = segStart; idx < segEnd && idx < N; idx++) {
          const val = cleaned[idx];
          if (!Number.isFinite(val)) continue;
          const diff = pre - val;
          if (diff > 0) area += diff;
        }
      }
      
      // Convert to percent-minutes
      percentMins += area / (60 * fs);
      
      // Update limit to prevent overlapping windows
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
      WinStart,        // Visualization window start (relative to event end)
      WinFinish,       // Visualization window end (relative to event end)
      HBWinStart: hbWinStart,   // HB calculation window start (-5s)
      HBWinFinish: hbWinFinish, // HB calculation window end (+45s)
      DurAvg,
      AvgGap,
      SleepHour: sleepHours
    }
  };
}

// ============================================================================
// Time Parsing & Math Utilities
// ============================================================================

function parseTimeValue(value) {
  if (value == null) return NaN;
  const str = String(value).trim();
  if (!str) return NaN;

  // Check for pure numeric value first
  if (/^-?\d+(\.\d+)?$/.test(str)) {
    return Number.parseFloat(str);
  }

  // Check for HH:MM:SS format (prioritize this over Date.parse)
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

  // Try Date.parse for full date-time strings
  const parsedDate = Date.parse(str);
  if (!Number.isNaN(parsedDate)) {
    return parsedDate / 1000;
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

// Adjust day shift: align event/hypnogram times to SpO2 reference
function adjustDayShift(t_ev, t_ref) {
  const meanRef = nanMean(t_ref);
  const meanEv = nanMean(t_ev);
  if (!Number.isFinite(meanRef) || !Number.isFinite(meanEv)) return t_ev;
  
  if (meanEv < meanRef - 12 * 3600) {
    return t_ev.map(x => Number.isFinite(x) ? x + 24 * 3600 : x);
  }
  if (meanEv > meanRef + 12 * 3600) {
    return t_ev.map(x => Number.isFinite(x) ? x - 24 * 3600 : x);
  }
  return t_ev;
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

// ============================================================================
// Main Processing Function
// ============================================================================

export async function computeHypoxicBurdenFromFiles(spo2Path, eventlistPath, hypnPath = null) {
  // Read files
  const spo2Text = fs.readFileSync(spo2Path, 'utf8');
  const eventText = fs.readFileSync(eventlistPath, 'utf8');
  const hypnText = hypnPath ? fs.readFileSync(hypnPath, 'utf8') : '';

  // Parse
  const spo2Rows = parseDelimited(spo2Text).rows;
  const eventRows = parseEventList(eventText);
  const hypnRows = hypnText ? parseDelimited(hypnText).rows : [];

  // Build data structures
  const spo2 = buildSpO2Series(spo2Rows);
  const sleepStage = buildSleepStage(hypnRows, spo2.absoluteTimes, spo2.t0);
  const events = alignEvents(eventRows, spo2.absoluteTimes, spo2.t0);

  if (!events.length) {
    throw new Error("No apnea/hypopnea/desaturation events found in the event list.");
  }

  // Calculate HB
  const { HB, result } = calcHBCore(spo2.values, 1, events, sleepStage);

  // === Sleep Indices (AHI, OAI, HI, ODI, REI, ArI, Sleep Efficiency) ===
  const totalSleepHours = result.SleepHour || 0;
  let apneaCount = 0;
  let hypopneaCount = 0;
  let desatCount = 0;
  let arousalCount = 0;

  for (const ev of events) {
    const t = (ev.Type || "").toLowerCase();
    if (t.includes("apnea")) apneaCount++;
    else if (t.includes("hypopnea")) hypopneaCount++;
    else if (t.includes("desat")) desatCount++;
    else if (t.includes("arousal")) arousalCount++;
  }

  const AHI = totalSleepHours > 0 ? (apneaCount + hypopneaCount) / totalSleepHours : null;
  const OAI = totalSleepHours > 0 ? apneaCount / totalSleepHours : null;
  const HI  = totalSleepHours > 0 ? hypopneaCount / totalSleepHours : null;
  const ODI = totalSleepHours > 0 ? desatCount / totalSleepHours : null;
  const REI = totalSleepHours > 0 ? (apneaCount + hypopneaCount + desatCount) / totalSleepHours : null;
  const ArI = totalSleepHours > 0 ? arousalCount / totalSleepHours : null;

  // Mean desaturation depth (optional)
  const desatDepths = events
    .filter(e => e.Type.toLowerCase().includes("desat"))
    .map(e => Number(e.Depth || e.MinSpO2 || NaN))
    .filter(Number.isFinite);
  const meanDesatDepth = desatDepths.length
    ? desatDepths.reduce((a, b) => a + b, 0) / desatDepths.length
    : null;

  // Sleep efficiency (sleep / total recording duration)
  let totalRecordingHours = 0;
  if (spo2.tSec && spo2.tSec.length > 1) {
    const totalSeconds = spo2.tSec[spo2.tSec.length - 1] - spo2.tSec[0];
    totalRecordingHours = totalSeconds / 3600;
  }
  const sleepEfficiency = totalRecordingHours > 0 ? (totalSleepHours / totalRecordingHours) * 100 : null;

  // Attach to result
  const indices = {
    AHI,      // Apnea-Hypopnea Index
    OAI,      // Obstructive Apnea Index
    HI,       // Hypopnea Index
    ODI,      // Oxygen Desaturation Index
    REI,      // Respiratory Event Index
    ArI,      // Arousal Index
    apneaCount,
    hypopneaCount,
    desatCount,
    arousalCount,
    meanDesatDepth,
    totalSleepHours,
    totalRecordingHours,
    sleepEfficiency
  };

  // Return JSON matching Python API format
  return {
    HB: Number.isFinite(HB) ? HB : null,
    SleepHour: Number.isFinite(result.SleepHour) ? result.SleepHour : null,
    t: safeFloatList(spo2.tSec),
    spo2: safeFloatList(spo2.values),
    sleep_t: safeFloatList(sleepStage.t),
    sleep_a: safeFloatList(sleepStage.Annotation),
    codes: sleepStage.Codes.slice(),
    desc: sleepStage.Description.slice(),
    events: events.map(ev => ({
      Start: ev.Start,
      Duration: ev.Duration,
      Type: ev.Type,
      Title: ev.Title || ''
    })),
    avg: safeFloatList(result.SpO2avg),
    filt: safeFloatList(result.SpO2avgfilt),
    std: safeFloatList(result.SpO2std),
    duravg: result.DurAvg,
    winstart: result.WinStart,
    winfinish: result.WinFinish,
    HBWinStart: result.HBWinStart,   // HB calculation window start (-5s relative to event end)
    HBWinFinish: result.HBWinFinish, // HB calculation window end (+45s relative to event end)
    nadirx: result.NadirIdx ?? 0,
    nadiry: result.Nadir,
    indices,
    pdf_url: "",
    xlsx_url: ""
  };
}
