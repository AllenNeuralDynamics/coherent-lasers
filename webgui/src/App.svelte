<script lang="ts">
  import LaserCards from "./lib/LaserCards.svelte";
  import LasersInfo from "./lib/LasersInfo.svelte";
  import type { Laser } from "./types";
  import LaserLogo from "/laser-logo.svg";

  async function generateMockLasers(
    count: number
  ): Promise<Record<string, Laser>> {
    const lasers: Record<string, Laser> = {};
    for (let i = 0; i < count; i++) {
      const serial = (Math.random() * 1e9).toFixed(0);
      lasers[serial] = {
        headInfo: {
          serial,
          type: "MiniX",
          hours: (Math.random() * 5000).toFixed(0),
          board_revision: "1.0",
          dio_status: "0",
        },
        signals: {
          power: Array.from({ length: 100 }, () => Math.random() * 200),
          powerSetpoint: Array.from({ length: 100 }, () => 100),
          lddCurrent: Array.from({ length: 10 }, () => Math.random()),
          lddCurrentLimit: Array.from({ length: 10 }, () => 0.75),
          mainTemperature: Array.from({ length: 10 }, () => 25),
          shgTemperature: Array.from({ length: 10 }, () => 25),
          brfTemperature: Array.from({ length: 10 }, () => 25),
          etalonTemperature: Array.from({ length: 10 }, () => 25),
        },
        flags: {
          interlock: Math.random() > 0.5,
          keySwitch: Math.random() > 0.5,
          softwareSwitch: Math.random() > 0.5,
          remoteControl: Math.random() > 0.5,
          analogInput: Math.random() > 0.5,
        },
      };
    }
    // Fake delay
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return lasers;
  }
</script>

<main>
  <div class="heading">
    <img src={LaserLogo} class="logo" alt="Laser Logo" />
    <h1>Genesis MX</h1>
  </div>
  {#await generateMockLasers(3)}
    <p class="fetch-indicator">Loading...</p>
  {:then lasers}
    <p class="fetch-indicator">Lasers: {Object.keys(lasers).length}</p>
    <div class="main-panel">
      <LaserCards {lasers} />
      <!-- <LasersInfo {lasers} /> -->
    </div>
  {:catch error}
    <p>Error: {error.message}</p>
  {/await}
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
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--zinc-600);
    background-color: var(--zinc-800);
    margin-block-end: 1rem;

    .logo {
      height: 1.75rem;
      will-change: filter;
      transition: filter 300ms;
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
    grid-template-columns: 1fr auto;
    height: 100%;
  }
</style>
