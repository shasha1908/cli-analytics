/**
 * CLI Analytics SDK for Node.js/TypeScript
 * Privacy-first analytics for CLI tools
 */

import { randomUUID } from 'crypto';

// Types
export interface InitOptions {
  apiKey: string;
  toolName: string;
  toolVersion?: string;
  endpoint?: string;
}

export interface TrackOptions {
  durationMs?: number;
  flags?: string[];
  sessionHint?: string;
  ciDetected?: boolean;
  metadata?: Record<string, unknown>;
}

interface Config {
  apiKey: string;
  toolName: string;
  toolVersion?: string;
  endpoint: string;
  actorId: string;
}

// Module state
let config: Config | null = null;

const DEFAULT_ENDPOINT = 'https://cli-analytics-1.onrender.com';

/**
 * Initialize the analytics SDK
 */
export function init(options: InitOptions): void {
  config = {
    apiKey: options.apiKey,
    toolName: options.toolName,
    toolVersion: options.toolVersion,
    endpoint: options.endpoint || DEFAULT_ENDPOINT,
    actorId: randomUUID(),
  };
}

/**
 * Track a CLI command execution
 */
export async function trackCommand(
  commandPath: string[],
  exitCode?: number,
  options?: TrackOptions
): Promise<void> {
  if (!config) {
    console.warn('[cli-analytics] SDK not initialized. Call init() first.');
    return;
  }

  const payload = {
    tool_name: config.toolName,
    tool_version: config.toolVersion,
    actor_id: config.actorId,
    command_path: commandPath,
    exit_code: exitCode,
    duration_ms: options?.durationMs,
    flags: options?.flags,
    session_hint: options?.sessionHint,
    ci_detected: options?.ciDetected,
    metadata: options?.metadata,
    timestamp: new Date().toISOString(),
  };

  try {
    const response = await fetch(`${config.endpoint}/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.apiKey,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      console.warn(`[cli-analytics] Failed to track: ${response.status}`);
    }
  } catch (error) {
    // Silently fail - don't break the CLI
  }
}

/**
 * Get A/B test variant for an experiment
 */
export async function getVariant(experimentName: string): Promise<string | null> {
  if (!config) {
    console.warn('[cli-analytics] SDK not initialized. Call init() first.');
    return null;
  }

  try {
    const url = `${config.endpoint}/experiments/${encodeURIComponent(experimentName)}/variant?actor_id=${encodeURIComponent(config.actorId)}`;
    const response = await fetch(url);

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data.variant || null;
  } catch (error) {
    return null;
  }
}

/**
 * Get recommendation for a command (useful after failures)
 */
export async function getRecommendation(
  command: string,
  failed: boolean = false
): Promise<string | null> {
  if (!config) {
    console.warn('[cli-analytics] SDK not initialized. Call init() first.');
    return null;
  }

  try {
    const url = `${config.endpoint}/recommendations?tool_name=${encodeURIComponent(config.toolName)}&command=${encodeURIComponent(command)}&failed=${failed}`;
    const response = await fetch(url);

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data.recommendation || null;
  } catch (error) {
    return null;
  }
}

/**
 * Tracker class for object-oriented usage
 */
export class Tracker {
  private apiKey: string;
  private toolName: string;
  private toolVersion?: string;
  private endpoint: string;
  private actorId: string;

  constructor(options: InitOptions) {
    this.apiKey = options.apiKey;
    this.toolName = options.toolName;
    this.toolVersion = options.toolVersion;
    this.endpoint = options.endpoint || DEFAULT_ENDPOINT;
    this.actorId = randomUUID();
  }

  async trackCommand(
    commandPath: string[],
    exitCode?: number,
    options?: TrackOptions
  ): Promise<void> {
    const payload = {
      tool_name: this.toolName,
      tool_version: this.toolVersion,
      actor_id: this.actorId,
      command_path: commandPath,
      exit_code: exitCode,
      duration_ms: options?.durationMs,
      flags: options?.flags,
      session_hint: options?.sessionHint,
      ci_detected: options?.ciDetected,
      metadata: options?.metadata,
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch(`${this.endpoint}/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        console.warn(`[cli-analytics] Failed to track: ${response.status}`);
      }
    } catch (error) {
      // Silently fail
    }
  }

  async getVariant(experimentName: string): Promise<string | null> {
    try {
      const url = `${this.endpoint}/experiments/${encodeURIComponent(experimentName)}/variant?actor_id=${encodeURIComponent(this.actorId)}`;
      const response = await fetch(url);

      if (!response.ok) return null;

      const data = await response.json();
      return data.variant || null;
    } catch (error) {
      return null;
    }
  }

  async getRecommendation(command: string, failed: boolean = false): Promise<string | null> {
    try {
      const url = `${this.endpoint}/recommendations?tool_name=${encodeURIComponent(this.toolName)}&command=${encodeURIComponent(command)}&failed=${failed}`;
      const response = await fetch(url);

      if (!response.ok) return null;

      const data = await response.json();
      return data.recommendation || null;
    } catch (error) {
      return null;
    }
  }
}
