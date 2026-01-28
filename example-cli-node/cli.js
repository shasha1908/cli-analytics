#!/usr/bin/env node
/**
 * Example Node.js CLI with cli-analytics integration
 */

const { Command } = require('commander');
const cliAnalytics = require('../sdk-node/dist');

// Initialize analytics
cliAnalytics.init({
  apiKey: 'cli__yT9ZNlxYHpkNghlGWVv7mXbMQ7CmUaC9nuLyzYn3Qw',
  toolName: 'mycli-node',
  toolVersion: '1.0.0',
  endpoint: 'https://cli-analytics-1.onrender.com',
});

const program = new Command();

program
  .name('mycli-node')
  .description('A sample Node.js CLI with analytics')
  .version('1.0.0');

// Helper to track and show recommendation on failure
async function track(command, exitCode, durationMs, flags = []) {
  await cliAnalytics.trackCommand(command, exitCode, { durationMs, flags });

  if (exitCode !== 0) {
    const hint = await cliAnalytics.getRecommendation(command[command.length - 1], true);
    if (hint) {
      console.log(`\x1b[33m💡 Tip: ${hint}\x1b[0m`);
    }
  }
}

program
  .command('init')
  .description('Initialize a new project')
  .action(async () => {
    console.log('Initializing project...');
    const start = Date.now();

    // Simulate work
    await new Promise(r => setTimeout(r, 500));

    const duration = Date.now() - start;
    console.log('\x1b[32m✓ Project initialized\x1b[0m');
    await track(['mycli-node', 'init'], 0, duration);
  });

program
  .command('build')
  .description('Build the project')
  .option('--env <env>', 'Target environment', 'dev')
  .action(async (options) => {
    console.log(`Building for ${options.env}...`);
    const start = Date.now();

    // Simulate work
    await new Promise(r => setTimeout(r, 1000));

    const duration = Date.now() - start;

    // Simulate occasional failure
    if (Math.random() < 0.3) {
      console.log('\x1b[31m✗ Build failed: missing dependencies\x1b[0m');
      await track(['mycli-node', 'build'], 1, duration, ['--env']);
      process.exit(1);
    }

    console.log('\x1b[32m✓ Build complete\x1b[0m');
    await track(['mycli-node', 'build'], 0, duration, ['--env']);
  });

program
  .command('deploy')
  .description('Deploy the project')
  .option('--force', 'Force deployment')
  .option('--env <env>', 'Target environment', 'dev')
  .action(async (options) => {
    // A/B test: try new deploy flow
    const variant = await cliAnalytics.getVariant('new-deploy-flow');

    if (variant === 'variant_a') {
      console.log(`[NEW FLOW] Deploying to ${options.env}...`);
    } else {
      console.log(`Deploying to ${options.env}...`);
    }

    const start = Date.now();

    // Simulate work
    await new Promise(r => setTimeout(r, 1500));

    const duration = Date.now() - start;

    const flags = ['--env'];
    if (options.force) flags.push('--force');

    // Simulate occasional failure
    if (Math.random() < 0.2) {
      console.log('\x1b[31m✗ Deploy failed: connection timeout\x1b[0m');
      await track(['mycli-node', 'deploy'], 1, duration, flags);
      process.exit(1);
    }

    console.log(`\x1b[32m✓ Deployed to ${options.env}\x1b[0m`);
    await track(['mycli-node', 'deploy'], 0, duration, flags);
  });

program
  .command('test')
  .description('Run tests')
  .action(async () => {
    console.log('Running tests...');
    const start = Date.now();

    // Simulate work
    await new Promise(r => setTimeout(r, 800));

    const duration = Date.now() - start;

    if (Math.random() < 0.25) {
      console.log('\x1b[31m✗ 2 tests failed\x1b[0m');
      await track(['mycli-node', 'test'], 1, duration);
      process.exit(1);
    }

    console.log('\x1b[32m✓ All tests passed\x1b[0m');
    await track(['mycli-node', 'test'], 0, duration);
  });

program.parse();
