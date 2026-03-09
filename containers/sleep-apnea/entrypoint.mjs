#!/usr/bin/env node
/**
 * NeuroHub Sleep Apnea technique container entrypoint.
 *
 * Wraps hb-calculator.js to compute Hypoxic Burden from SpO2, Hypnogram,
 * and EventList files.
 *
 * Mounts:
 *   /input  — directory containing uploaded files (CSV + TXT)
 *   /output — output directory for results JSON + HTML report
 *
 * Outputs NEUROHUB_OUTPUT JSON to stdout (NeuroHub convention).
 */

import fs from "fs";
import path from "path";
import { computeHypoxicBurdenFromFiles } from "./hb-calculator.js";

const MODULE_KEY = "Sleep_Apnea_Analysis";
const MODULE_VERSION = "1.0.0";

const INPUT_DIR = "/input";
const OUTPUT_DIR = "/output";

function findFile(dir, patterns) {
  const files = [];
  try {
    const entries = fs.readdirSync(dir, { recursive: true });
    for (const entry of entries) {
      const full = path.join(dir, entry);
      if (!fs.statSync(full).isFile()) continue;
      files.push(full);
    }
  } catch {
    return null;
  }

  for (const pattern of patterns) {
    const re = new RegExp(pattern, "i");
    const match = files.find((f) => re.test(path.basename(f)));
    if (match) return match;
  }
  return null;
}

async function main() {
  console.error(`[${MODULE_KEY}] Starting Hypoxic Burden analysis...`);
  console.error(`[${MODULE_KEY}] Input dir: ${INPUT_DIR}`);

  // Find input files
  const spo2File = findFile(INPUT_DIR, [
    "osat", "spo2", "o2sa", "alltrends.*osat",
    "alltrends.*sat", "oxygen",
  ]);
  const eventFile = findFile(INPUT_DIR, [
    "eventlist", "event_list", "events",
  ]);
  const hypnFile = findFile(INPUT_DIR, [
    "hypnogram", "hypn", "alltrends.*hypn",
    "sleep.*stage",
  ]);

  if (!spo2File) {
    console.error(`[${MODULE_KEY}] ERROR: No SpO2 CSV file found in ${INPUT_DIR}`);
    process.exit(1);
  }
  if (!eventFile) {
    console.error(`[${MODULE_KEY}] ERROR: No event list file found in ${INPUT_DIR}`);
    process.exit(1);
  }

  console.error(`[${MODULE_KEY}] SpO2: ${spo2File}`);
  console.error(`[${MODULE_KEY}] Events: ${eventFile}`);
  console.error(`[${MODULE_KEY}] Hypnogram: ${hypnFile || "not provided"}`);

  // Run calculation
  const result = await computeHypoxicBurdenFromFiles(spo2File, eventFile, hypnFile);

  // Write results JSON
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const resultsPath = path.join(OUTPUT_DIR, "results.json");
  fs.writeFileSync(resultsPath, JSON.stringify(result, null, 2));
  console.error(`[${MODULE_KEY}] Results written to ${resultsPath}`);

  // Build features for NeuroHub
  const features = {
    hypoxic_burden: result.HB,
    sleep_hours: result.SleepHour,
    ahi: result.indices?.AHI,
    oai: result.indices?.OAI,
    hi: result.indices?.HI,
    odi: result.indices?.ODI,
    rei: result.indices?.REI,
    apnea_count: result.indices?.apneaCount,
    hypopnea_count: result.indices?.hypopneaCount,
    desat_count: result.indices?.desatCount,
    sleep_efficiency: result.indices?.sleepEfficiency,
    total_events: result.events?.length || 0,
  };

  // Build maps (visualization data stored as maps)
  const maps = {};
  if (result.spo2 && result.t) {
    maps.spo2_timeseries = { t: result.t, values: result.spo2 };
  }
  if (result.avg && result.filt) {
    maps.avg_response = {
      avg: result.avg,
      filt: result.filt,
      duravg: result.duravg,
      winstart: result.winstart,
      winfinish: result.winfinish,
      nadirx: result.nadirx,
      nadiry: result.nadiry,
    };
  }
  if (result.events) {
    maps.events = result.events;
  }
  if (result.sleep_t && result.sleep_a) {
    maps.sleep_stages = { t: result.sleep_t, annotations: result.sleep_a };
  }

  // Determine severity
  let severity = "정상";
  const ahi = result.indices?.AHI;
  if (ahi != null) {
    if (ahi >= 30) severity = "중증";
    else if (ahi >= 15) severity = "중등도";
    else if (ahi >= 5) severity = "경증";
  }
  features.severity = severity;

  // QC score
  const qc = result.events?.length > 0 && result.HB != null ? 90 : 50;

  // NeuroHub output format
  const output = {
    module_key: MODULE_KEY,
    module_version: MODULE_VERSION,
    status: "success",
    features,
    maps,
    feature_count: Object.keys(features).length,
    map_count: Object.keys(maps).length,
    qc_score: qc,
    metadata: {
      spo2_samples: result.spo2?.length || 0,
      event_count: result.events?.length || 0,
      has_hypnogram: !!hypnFile,
    },
  };

  // Print NEUROHUB_OUTPUT to stdout (convention)
  console.log("NEUROHUB_OUTPUT " + JSON.stringify(output));
  console.error(`[${MODULE_KEY}] Done. HB=${result.HB?.toFixed(3)}, AHI=${ahi?.toFixed(1)}, severity=${severity}`);
}

main().catch((err) => {
  console.error(`[${MODULE_KEY}] FATAL:`, err.message);
  process.exit(1);
});
