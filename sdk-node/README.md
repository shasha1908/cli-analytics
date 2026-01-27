# CLI Analytics - Node.js SDK

Privacy-first analytics for CLI tools.

## Install

```bash
npm install cli-analytics
```

## Quick Start

```typescript
import * as cliAnalytics from 'cli-analytics';

// Initialize once at startup
cliAnalytics.init({
  apiKey: 'cli_xxx',
  toolName: 'mycli',
  toolVersion: '1.0.0',
});

// Track commands
await cliAnalytics.trackCommand(['mycli', 'deploy'], 0, {
  durationMs: 1500,
  flags: ['--force', '--env'],
});
```

## API

### `init(options)`

Initialize the SDK. Call once at CLI startup.

```typescript
cliAnalytics.init({
  apiKey: 'cli_xxx',        // Required: Your API key
  toolName: 'mycli',        // Required: CLI name
  toolVersion: '1.0.0',     // Optional: CLI version
  endpoint: 'https://...',  // Optional: Custom endpoint
});
```

### `trackCommand(commandPath, exitCode?, options?)`

Track a command execution.

```typescript
await cliAnalytics.trackCommand(
  ['mycli', 'deploy', 'prod'],  // Command path
  0,                             // Exit code (0 = success)
  {
    durationMs: 1500,            // Execution time
    flags: ['--force'],          // Flags used (values stripped)
    ciDetected: true,            // Running in CI?
  }
);
```

### `getVariant(experimentName)`

Get A/B test variant assignment.

```typescript
const variant = await cliAnalytics.getVariant('new-deploy-flow');
if (variant === 'variant_a') {
  // New flow
} else {
  // Control
}
```

### `getRecommendation(command, failed?)`

Get usage-based recommendation.

```typescript
if (exitCode !== 0) {
  const hint = await cliAnalytics.getRecommendation('deploy', true);
  if (hint) {
    console.log(`Tip: ${hint}`);
  }
}
```

## Class-based Usage

```typescript
import { Tracker } from 'cli-analytics';

const tracker = new Tracker({
  apiKey: 'cli_xxx',
  toolName: 'mycli',
});

await tracker.trackCommand(['mycli', 'build'], 0);
const variant = await tracker.getVariant('experiment-name');
```

## Local Development

```bash
cd sdk-node
npm install
npm run build
```

To test locally without publishing:

```bash
npm link
# In your CLI project:
npm link cli-analytics
```
