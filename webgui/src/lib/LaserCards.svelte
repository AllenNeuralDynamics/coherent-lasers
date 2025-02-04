<script lang="ts">
  import { LaserPowerChart } from "../state.svelte";
  import type { Laser } from "../types";
  import DeliminatedInput from "./DeliminatedInput.svelte";

  let { lasers }: { lasers: Record<string, Laser> } = $props();
</script>

{#snippet laserFlag(
  flagLabel: string,
  flag: boolean,
  readonly: boolean = false
)}
  <button
    style:--indicator-color={flag ? "lime" : "crimson"}
    disabled={readonly}
  >
    <div class="indicator"></div>
    <span class="flag-name">
      {flagLabel.replace(/([A-Z])/g, " $1")}
    </span>
  </button>
{/snippet}

<div class="laser-cards">
  {#each Object.entries(lasers) as [serial, laser]}
    <div class="laser-card">
      <h2>{serial}</h2>
      <div class="laser-flags">
        {@render laserFlag("Remote Control", laser.flags.remoteControl)}
        {@render laserFlag("Software Switch", laser.flags.softwareSwitch)}
        {@render laserFlag("Analog Input", laser.flags.analogInput)}
        {@render laserFlag("Interlock", laser.flags.interlock, true)}
        {@render laserFlag("Key Switch", laser.flags.keySwitch, true)}
      </div>
      <div class="laser-power">
        <p class="text-sm zinc-300">Power (mW)</p>
        <div class="chart-container">
          <svg use:LaserPowerChart={laser}></svg>
        </div>
        <div class="setpoint-input">
          <p>Power Setpoint (mW)</p>
          <DeliminatedInput
            value={laser.signals.powerSetpoint[
              laser.signals.powerSetpoint.length - 1
            ]}
            min={0}
            max={1000}
            step={1}
            onChange={(value) => console.log(value)}
          />
        </div>
      </div>
    </div>
  {/each}
</div>

<style>
  .laser-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(40rem, 1fr));
    /* grid-template-rows: repeat(auto-fill, minmax(24rem, 1fr)); */
    grid-template-rows: max-content;
    gap: 1rem;
    padding-inline: 1rem;
    margin-block-end: 1rem;
    overflow: auto;
  }

  .laser-card {
    --inline-spacing: 0.75rem;
    --block-spacing: 0.5rem;
    --border-radius: 0;
    --border: 1px solid var(--zinc-600);
    border: var(--border);
    border-radius: var(--border-radius);
    background-color: var(--zinc-900);
    color: var(--zinc-300);
    display: flex;
    flex-direction: column;
    height: max-content;
  }

  .laser-card h2 {
    padding-inline: var(--inline-spacing);
    padding-block: var(--block-spacing);
    font-size: var(--font-md);
    font-weight: 500;
    color: var(--zinc-400);
    background-color: var(--zinc-800);
  }
  .laser-flags {
    --transition-duration: 0.3s;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    gap: var(--block-spacing) calc(var(--inline-spacing) * 2);
    padding: 1rem 0.75rem;
    border-block: var(--border);
  }

  .laser-flags > button {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: var(--font-sm);
    border: 1px solid var(--zinc-600);
    padding: 0.5rem;
    border-radius: 0.5rem;
    transition: all var(--transition-duration) ease-in-out;
    &:disabled {
      color: var(--zinc-300);
      background-color: var(--zinc-800);
      border-color: transparent;
      cursor: default;
    }
    div.indicator {
      width: 1rem;
      aspect-ratio: 1;
      border-radius: 50%;
      background-color: var(--indicator-color, var(--zinc-700));
    }
    &:hover,
    &:focus,
    &:focus-visible {
      &:not(:disabled) {
        outline: none;
        border-color: var(--zinc-500);
        background-color: var(--zinc-800);
      }
    }
  }

  .laser-power {
    --border-color: var(--zinc-600);
    --border-hover-color: var(--zinc-500);
    --thumb-color: var(--yellow-400);
    --thumb-hover-color: var(--yellow-400);
    --transition-duration: 0.2s;
    flex-grow: 1;
    padding: 1rem 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .laser-power .chart-container {
    /* border: 1px solid var(--zinc-700); */
    background-color: var(--zinc-900);
    /* flex: 1; */
    height: clamp(16rem, 20vh, 16rem);
    /* height: max-content; */
    > svg {
      width: 100%;
      height: 100%;
    }
  }
  .laser-power .setpoint-input {
    display: grid;
    grid-template-columns: auto 1fr auto;
    transition: all var(--transition-duration) ease-in-out;
    background-color: var(--zinc-800);
    > p {
      border: var(--border);
      padding-inline: 0.5rem;
      display: flex;
      align-items: center;
      height: calc(100% - 0.2rem);
      font-size: var(--font-sm);
      color: var(--zinc-300);
      transition:
        color var(--transition-duration) ease-in-out,
        background-color var(--transition-duration) ease-in-out,
        border-color var(--transition-duration) ease-in-out;
      &:first-child {
        border-inline-end: none;
      }
    }
    &:hover,
    &:focus,
    &:focus-visible {
      > p {
        color: var(--zinc-300);
        background-color: var(--zinc-700);
        border-color: var(--border-hover-color);
      }
      /* outline: none;
      background-color: var(--zinc-700); */
    }
  }
</style>
