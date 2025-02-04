<script lang="ts">
  import LaserCards from "./lib/LaserCards.svelte";
  import { GenesisMXState } from "./state.svelte";
  import LaserLogo from "/laser-logo.svg";
  const appState = new GenesisMXState();
</script>

<main>
  <div class="heading">
    <div class="app-name">
      <img src={LaserLogo} class="logo" alt="Laser Logo" />
      <h1>Genesis MX</h1>
    </div>
    <div class="controls">
      <label for="power-limit">Max Power</label>
      <input type="number" bind:value={appState.powerLimit} />
      {#if appState.isRunning}
        <button class="running" onclick={() => appState.stop()}>
          <span>Stop</span>
        </button>
      {:else}
        <button onclick={() => appState.init().then(() => {})}>
          <span>Start</span>
        </button>
      {/if}
    </div>
  </div>
  <div class="main-panel">
    {#if appState.isRunning}
      {@const lasers = appState.lasers}
      <LaserCards {lasers} />
    {:else}
      <p class="fetch-indicator">Click the Start button to begin</p>
    {/if}
  </div>
</main>

<style>
  main {
    display: flex;
    flex-direction: column;
    width: 100dvw;
    height: 100dvh;
    overflow: hidden;
  }

  .heading {
    display: flex;
    align-items: center;
    gap: 1rem;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--zinc-600);
    background-color: var(--zinc-900);
    margin-block-end: 1rem;

    .app-name {
      display: flex;
      align-items: center;
      gap: 1rem;
      .logo {
        height: 1.5rem;
        will-change: filter;
        transition: filter 300ms;
      }
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 1rem;
      label {
        font-size: var(--font-lg);
        color: var(--zinc-400);
      }

      button {
        font-size: var(--font-lg);
        padding: 0.5rem 1rem;
        min-width: 6rem;
        --color: var(--emerald-500);
        --bg-color: color-mix(in srgb, var(--color) 10%, transparent);
        color: var(--color);
        background-color: var(--bg-color);
        border: 1px solid var(--color);
        &.running {
          --color: var(--rose-500);
        }
        &:hover,
        &:focus,
        &:focus-visible {
          outline: none;
          --bg-color: color-mix(in srgb, var(--color) 20%, transparent);
        }
      }
      input[type="number"] {
        width: 6rem;
        padding: 0.5rem;
        font-size: var(--font-lg);
        border: 1px solid var(--zinc-600);
        background-color: var(--zinc-900);
        color: var(--zinc-300);
        outline: none;
        &:hover,
        &:focus,
        &:focus-visible {
          outline: none;
          border-color: var(--zinc-500);
        }
      }
    }
  }
  .fetch-indicator {
    padding-inline: 1rem;
    margin-block-end: 1rem;
    font-size: var(--font-md);
    color: var(--zinc-300);
  }
  .main-panel {
    display: grid;
    grid-template-rows: max-content;
    height: 100%;
  }
</style>
