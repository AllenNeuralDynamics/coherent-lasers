<script lang="ts">
  import { LaserPowerChart, Laser } from "../state.svelte";
  let { laser }: { laser: Laser } = $props();
  import DeliminatedInput from "./DeliminatedInput.svelte";

  function toggleSoftwareSwitch() {
    if (laser.flags.softwareSwitch) {
      laser.disable();
    } else {
      laser.enable();
    }
  }
  function toggleRomoteControl() {
    laser.toggleRemoteControl();
  }
</script>

{#snippet laserFlag(flagLabel: string, flag: boolean)}
  <button class:on={flag} disabled>
    <div class="indicator"></div>
    <span class="flag-name">
      {flagLabel.replace(/([A-Z])/g, " $1")}
    </span>
  </button>
{/snippet}

{#snippet remoteControlIcon()}
  <button onclick={toggleRomoteControl}>
    {#if laser.flags.remoteControl}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        aria-label="Remote Control Enabled"
      >
        <g
          fill="none"
          stroke="var(--emerald-500)"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
        >
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 9.9-1" />
        </g>
      </svg>
    {:else}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        aria-label="Remote Control Disabled"
      >
        <g
          fill="none"
          stroke="var(--rose-500)"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
        >
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </g>
      </svg>
    {/if}
  </button>
{/snippet}

<div class="laser-card">
  <div class="card-header">
    <h2>{laser.head.serial}</h2>
    {@render remoteControlIcon()}
  </div>
  <div class="laser-power">
    <div class="chart-container">
      <svg use:LaserPowerChart={laser}></svg>
    </div>
    <div class="setpoint-input">
      <p>Power</p>
      <p>{laser.power[laser.power.length - 1].toFixed(2)}</p>
      <p>Setpoint</p>
      <DeliminatedInput
        value={laser.powerSetpoint[laser.powerSetpoint.length - 1]}
        min={0}
        max={laser.powerLimit}
        step={1}
        onChange={(value) => laser.setPower(value)}
      />
    </div>
  </div>
  <div class="laser-flags">
    <button
      class:on={laser.flags.softwareSwitch}
      onclick={toggleSoftwareSwitch}
      disabled={!(
        laser.flags.interlock &&
        laser.flags.keySwitch &&
        laser.flags.remoteControl
      )}
    >
      <div class="indicator"></div>
      <span class="flag-name">Software Switch</span>
    </button>

    {@render laserFlag("Interlock", laser.flags.interlock)}
    {@render laserFlag("Key Switch", laser.flags.keySwitch)}
    <!-- {@render laserFlag("Analog Input", laser.flags.analogInput)} -->
  </div>
</div>

<style>
  .laser-card {
    --inline-spacing: 0.75rem;
    --block-spacing: 0.5rem;
    --border-radius: 0.5rem;
    --border: 1px solid var(--zinc-700);
    border: var(--border);
    border-radius: var(--border-radius);
    background-color: var(--zinc-900);
    color: var(--zinc-300);
    display: flex;
    flex-direction: column;
    gap: var(--block-spacing);
    height: max-content;
    overflow: hidden;
  }
  .laser-card .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-inline: var(--inline-spacing);
    padding-block: var(--block-spacing);
    background-color: var(--zinc-900);
    border-bottom: var(--border);
    h2 {
      font-size: var(--font-md);
      font-weight: 300;
      color: var(--zinc-400);
      text-transform: uppercase;
    }
    svg {
      opacity: 0.65;
    }
    button:hover,
    button:focus,
    button:focus-visible {
      outline: none;
      svg {
        opacity: 1;
      }
    }
  }

  .laser-flags {
    --transition-duration: 0.3s;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    gap: 1rem calc(var(--inline-spacing) * 2);
    padding: 1rem 0.75rem;
  }

  .laser-flags > button {
    --color: var(--rose-200);
    --indicator-color: var(--rose-500);
    --border-color: color-mix(in srgb, var(--indicator-color) 50%, transparent);
    --bg-color: color-mix(in srgb, var(--indicator-color) 10%, transparent);
    border: 1px solid var(--border-color);
    background-color: var(--bg-color);
    color: var(--color);
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem;
    border-radius: 0.5rem;
    transition: all var(--transition-duration) ease-in-out;
    &:disabled {
      --border-color: color-mix(
        in srgb,
        var(--indicator-color) 30%,
        transparent
      );
      --bg-color: transparent;
      cursor: default;
    }
    &.on {
      --indicator-color: var(--emerald-500);
      --color: var(--emerald-200);
    }
    div.indicator {
      width: 1rem;
      aspect-ratio: 1;
      border-radius: 50%;
      background-color: var(--indicator-color);
    }
    &:hover,
    &:focus,
    &:focus-visible {
      &:not(:disabled) {
        outline: none;
        --bg-color: color-mix(in srgb, var(--indicator-color) 20%, transparent);
      }
    }
    .flag-name {
      text-transform: capitalize;
      font-size: var(--font-md);
      font-weight: 300;
    }
  }

  .laser-power {
    --border-color: var(--zinc-700);
    --border-hover-color: var(--zinc-600);
    --thumb-color: var(--zinc-400);
    --thumb-hover-color: var(--yellow-400);
    --transition-duration: 0.2s;
    flex-grow: 1;
    padding-block: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .laser-power {
    padding-inline: Var(--inline-spacing);
  }
  .laser-power .setpoint-input {
    display: grid;
    grid-template-columns: 5rem 1fr;
    gap: 1rem;
    p {
      font-size: var(--font-lg);
      font-weight: 300;
      color: var(--zinc-400);
    }
  }
  .laser-power .chart-container {
    border: var(--border);
    border-radius: calc(var(--border-radius) / 2);
    height: clamp(16rem, 20vh, 16rem);
    display: flex;
    > svg {
      flex: 1;
      height: 100%;
    }
  }
</style>
