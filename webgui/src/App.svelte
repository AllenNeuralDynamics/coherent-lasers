<script lang="ts">
  import { untrack } from "svelte";
  import LaserLogo from "/laser-logo.svg";
  import * as d3 from "d3";
  import { laserPowerChart } from "./chart.svelte";
  import { Laser } from "./laser.svelte";

  const API_BASE: string = "http://localhost:8000/api";
  const MIN_POWER = 0;

  // State
  let lasers = $state<Laser[]>([]);
  let maxPower = $state<number>(10);
  let powerLimit = $state<number>(1000);
  let loading = $state<boolean>(false);

  async function fetchLasers(): Promise<Laser[]> {
    untrack(() => {
      lasers.forEach((laser) => laser.unsubscribe());
      lasers = [];
      loading = true;
    });
    const res = await fetch(`${API_BASE}/devices`);
    if (!res.ok) {
      throw new Error("Failed to fetch devices.");
    }
    const serials = await res.json();
    console.log("serials: ", serials);
    lasers = serials.map((serial: string) => new Laser(serial));
    loading = false;
    return lasers;
  }

  function getIndicatorColor(prop: boolean | null | undefined): string {
    if (prop === null || prop === undefined) {
      return "var(--zinc-500)";
    }
    return prop ? "var(--emerald-500)" : "var(--rose-500)";
  }

  $effect(() => {
    const MIN_RANGE = 10;
    const INCREMENT = 10;
    const maxValues = lasers.flatMap((laser) => [
      d3.max(laser.history, (d) => d.power.value) ?? 0,
      d3.max(laser.history, (d) => d.power.setpoint) ?? 0,
    ]);

    const collectiveMax = Math.max(...maxValues);
    const closestMultiple = Math.ceil(collectiveMax / INCREMENT) * INCREMENT;
    maxPower = Math.max(closestMultiple, MIN_POWER + MIN_RANGE);
  });
</script>

{#snippet spinner(className: string = "")}
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    class={className}
  >
    <circle cx="12" cy="12" r="0" fill="currentColor">
      <animate
        attributeName="r"
        calcMode="spline"
        dur="1.2s"
        keySplines=".52,.6,.25,.99"
        repeatCount="indefinite"
        values="0;11"
      />
      <animate
        attributeName="opacity"
        calcMode="spline"
        dur="1.2s"
        keySplines=".52,.6,.25,.99"
        repeatCount="indefinite"
        values="1;0"
      />
    </circle>
  </svg>
{/snippet}

{#snippet laserCard(laser: Laser)}
  <div class="laser-card">
    <div class="header">
      <h2 class="text-md zinc-400">{laser.serial}</h2>
      <div class="quick-controls">
        {#if laser.status}
          <button
            aria-label="Toggle Remote Control"
            class="remote-control"
            disabled={laser.status.remote_control === null}
            style:--btn-accent={laser.status.remote_control == null
              ? "var(--zinc-500)"
              : laser.status.remote_control
                ? "var(--emerald-500)"
                : "var(--rose-500)"}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              width="20"
              height="20"
            >
              <title>Remote Control</title>
              <path
                fill="none"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="m7 12l4.95 4.95L22.557 6.343M2.05 12.05L7 17M17.606 6.394l-5.303 5.303"
              />
            </svg>
          </button>
        {/if}
        <button
          onclick={() => laser.refreshStatus()}
          aria-label="Refresh laser status"
          class="refresh"
          style:--btn-accent={laser.status == null
            ? "var(--rose-500)"
            : "var(--emerald-500)"}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            width="18"
            height="18"
          >
            <title>Refresh</title>
            <path
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 16H5v5m9-13h5V3M4.583 9.003a8 8 0 0 1 14.331-1.027m.504 7.021a8 8 0 0 1-14.332 1.027"
            />
          </svg>
        </button>
      </div>
    </div>
    <div class="enable-loop">
      <div style:--indicator={getIndicatorColor(laser.status?.software_switch)}>
        <h3 class="label">Software</h3>
        <div class="indicator"></div>
      </div>
      <div style:--indicator={getIndicatorColor(laser.status?.key_switch)}>
        <h3 class="label">Key</h3>
        <div class="indicator"></div>
      </div>
      <div style:--indicator={getIndicatorColor(laser.status?.interlock)}>
        <h3 class="label">Interlock</h3>
        <div class="indicator"></div>
      </div>
    </div>
    <div class="power">
      {#if laser.connected && laser.history.length > 1}
        <div class="chart-container">
          <svg
            use:laserPowerChart={{
              laser: laser,
              getPowerRange: () => [MIN_POWER, maxPower],
            }}
          ></svg>
        </div>
      {:else}
        <div class="chart-placeholder">
          {@render spinner()}
        </div>
      {/if}
      <div class="properties">
        <div class="power-value property">
          <h3>Power</h3>
          <p>{laser.power.value?.toFixed(2) ?? "--"} <small>mW</small></p>
        </div>
        <div class="power-setpoint property">
          <h3>Setpoint</h3>
          <p>{laser.power.setpoint?.toFixed(2) ?? "--"} <small>mW</small></p>
        </div>
        <div class="current property">
          <h3>Current</h3>
          <p>{laser.status?.current?.toFixed(2) ?? "--"} <small>A</small></p>
        </div>
        <div class="temperature property">
          <h3>Temp</h3>
          <p>
            {laser.status?.temperature?.toFixed(2) ?? "--"} <small>℃</small>
          </p>
        </div>
      </div>
    </div>

    <div class="footer">
      <div class="controls">
        <button
          class="enable-button"
          class:enabling={laser.enabling}
          onclick={() => laser.enable()}
        >
          <span> Enable </span>
          {#if laser.enabling}
            {@render spinner("indicator")}
          {/if}
        </button>
        <button class="disable-button" onclick={() => laser.disable()}>
          <span>Disable</span>
        </button>
        <input
          type="number"
          data-serial={laser.serial}
          min="0"
          max={powerLimit}
          step="1"
          value={laser.power.setpoint}
          disabled={!laser.status || laser.status.power.setpoint === null}
          onchange={(e) => {
            const target = e.target as HTMLInputElement;
            const value = Math.min(
              Math.max(parseFloat(target.value), parseInt(target.min)),
              parseInt(target.max)
            );
            target.value = value.toString();
            laser.setPower(value);
          }}
          onclick={(e) => {
            const target = e.target as HTMLInputElement;
            target && target.select();
          }}
        />
      </div>
    </div>
  </div>
{/snippet}

<main>
  <section class="header">
    <div class="app-name">
      <img src={LaserLogo} class="logo" alt="Laser Logo" />
      <h1>Genesis MX</h1>
    </div>
    <div class="app-controls">
      <div class="input">
        <label for="power-limit">Power Limit (mW)</label>
        <input
          name="power-limit"
          type="number"
          min="10"
          max="1000"
          step="10"
          bind:value={powerLimit}
          onchange={(e) => {
            const target = e.target as HTMLInputElement;
            const value = Math.min(
              Math.max(parseFloat(target.value), parseInt(target.min)),
              parseInt(target.max)
            );
            target.value = value.toString();
            powerLimit = value;
            lasers.forEach((laser) => {
              if (
                laser.power.setpoint !== undefined &&
                laser.power.setpoint > powerLimit
              ) {
                laser.setPower(powerLimit * 0.8);
              }
            });
          }}
        />
      </div>
      <button onclick={() => fetchLasers()}>Refresh</button>
    </div>
  </section>
  <section class="laser-cards">
    {#await fetchLasers()}
      <div>
        {@render spinner()}
        <p>Loading devices...</p>
      </div>
    {:then _}
      {#if loading}
        <div>
          {@render spinner()}
          <p>Loading devices...</p>
        </div>
      {:else if lasers.length === 0}
        <p>No devices found.</p>
      {:else}
        {#each lasers as laser}
          {@render laserCard(laser)}
        {/each}
      {/if}
    {:catch error}
      <div class="error">Error: {error.message}</div>
    {/await}
  </section>
</main>

<style>
  main {
    max-width: 88rem;
    margin-inline: auto;
    padding: 1rem;
    input[type="number"]::-webkit-inner-spin-button {
      appearance: none;
    }
    > .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      .app-controls {
        display: flex;
        align-items: center;
        gap: 1rem;
      }
      button,
      input {
        padding-inline: 1rem;
        height: 2rem;
        text-align: center;
        font-size: var(--font-md);
        line-height: 100%;
        font-weight: 300;
      }
      label {
        font-size: var(--font-sm);
        color: var(--zinc-400);
        margin-inline-end: 0.5rem;
      }
      button {
        /* padding: 0.65rem 1rem; */
        border-radius: 0.25rem;
        border: 1px solid var(--zinc-700);
        background-color: var(--zinc-800);
        transition:
          color 0.3s,
          background-color 0.3s;
        &:hover {
          background-color: var(--yellow-500);
          color: var(--zinc-900);
        }
      }
      input {
        width: 5rem;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border: 1px solid var(--zinc-700);
        background-color: var(--zinc-800);
        transition: border-color 0.3s;
        &:hover,
        &:focus {
          border-color: var(--zinc-600);
        }
      }
    }
    .app-name {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      .logo {
        height: 1.5rem;
      }
    }
  }
  .laser-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(24rem, 1fr));
    grid-template-rows: max-content;
    gap: 1rem;
    margin-block: 1rem;
  }
  .laser-card {
    --padding: 1rem;
    --card-border: 1px solid var(--zinc-700);
    border: 1px solid var(--zinc-700);
    border-radius: 0.25rem;
    overflow: hidden;
    display: grid;
    grid-template-rows: repeat(4, max-content);
    .header {
      background-color: var(--zinc-900);
      /* border-block-end: var(--card-border); */
      padding-inline: var(--padding) calc(var(--padding) - 0.25rem);
      height: 2.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;

      .quick-controls {
        display: flex;
        gap: 0.25rem;
        button {
          width: 2rem;
          aspect-ratio: 1;
          border-radius: 50%;
          border: none;
          cursor: pointer;
          background-color: transparent;
          transition: background-color 0.3s;
          color: var(--btn-accent, var(--zinc-500));
          &:disabled {
            cursor: var(--not-allowed-cursor, not-allowed);
          }
          &:not(:disabled):hover {
            background-color: var(--zinc-800);
          }
        }
      }
    }
    .enable-loop {
      display: flex;
      justify-content: space-between;
      align-items: center;
      user-select: none;
      background-color: var(--zinc-950);
      padding-inline: var(--padding);
      padding-block: var(--padding);
      border-block-end: var(--card-border);
      > div {
        display: flex;
        align-items: center;
        flex-direction: row-reverse;
        gap: 0.5rem;
        padding: 0.125rem 0.5rem;
        width: 7rem;
        --border-color: color-mix(
          in srgb,
          var(--indicator, var(--zinc-500)) 50%,
          transparent
        );
        background-color: color-mix(
          in srgb,
          var(--indicator, var(--zinc-500)) 10%,
          transparent
        );
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
        overflow: hidden;
        .label {
          font-size: var(--font-sm);
          font-weight: 500;
          color: var(--zinc-400);
          color: var(--indicator, var(--zinc-500));
          flex: 1;
        }
        .indicator {
          width: 1rem;
          aspect-ratio: 1;
          border-radius: 50%;
          background-color: var(--indicator, var(--zinc-500));
        }
      }
    }
    .power {
      display: grid;
      grid-template-columns: 1fr auto;
      margin-inline-end: var(--padding);
      .power-setpoint {
        color: var(--yellow-400);
      }
      .power-value {
        color: var(--cyan-400);
      }
      .properties {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding-inline: 0.25rem;
        padding-top: 20px;
        padding-bottom: 25px;
        height: clamp(12rem, 16vw, 16rem);
        height: max-content;
        gap: 0.25rem;
        .property {
          display: flex;
          flex-direction: column;
          font-size: var(--font-sm);
          padding-block: 0.25rem;
          border-block-start: 1px solid var(--zinc-700);
          &:last-child {
            border-block-end: 1px solid var(--zinc-700);
          }
          h3 {
            font-size: var(--font-xs);
            font-weight: 500;
            color: var(--zinc-400);
          }
          p {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
          }
        }
      }
      .chart-placeholder {
        display: grid;
        place-content: center;
        color: var(--zinc-500);
        background-color: color-mix(
          in srgb,
          var(--zinc-900) 50%,
          var(--zinc-800)
        );
        border-radius: 0.25rem;
        filter: blur(1px);
        margin: calc(var(--padding) + 0.25rem);
      }
      .chart-container {
        height: clamp(12rem, 16vw, 16rem);
        height: 100%;
        display: flex;
        > svg {
          flex: 1;
          height: 100%;
        }
      }
    }
    .footer {
      background-color: var(--zinc-900);
      .controls {
        display: grid;
        grid-template-columns: 2fr 2fr 3fr;
        gap: 1rem;
        padding: var(--padding);
        button,
        input {
          color: var(--zinc-50);
          font-size: var(--font-md);
          font-weight: 400;
          height: 2rem;
          border-radius: 0.25rem;
          border: 1px solid var(--color);
        }
        input {
          --color: var(--yellow-400);
          background-color: var(--zinc-900);
          text-align: center;
          transition: border-color 0.3s;
          &:hover,
          &:focus {
            --color: var(--yellow-600);
          }
          &:disabled {
            background-color: var(--zinc-900);
            cursor: not-allowed;
            opacity: 0.5;
          }
        }
        button {
          cursor: pointer;
          user-select: none;
          background-color: transparent;
          transition: background-color 0.3s;
          background-color: color-mix(in srgb, var(--color) 15%, transparent);
          position: relative;
          padding-inline: 0.5rem;
          &.enable-button {
            --color: var(--cyan-700);
          }
          &.enable-button.enabling {
            pointer-events: none;
            cursor: var(--not-allowed-cursor);
            color: var(--color);
            overflow: hidden;
            span {
              opacity: 0;
            }
          }
          &.disable-button {
            --color: var(--rose-700);
          }
          &:hover {
            background-color: var(--color);
            color: var(--zinc-50);
          }
          .indicator {
            width: 2rem;
            aspect-ratio: 1;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
          }
        }
      }
    }
  }
  .error {
    color: var(--rose-600);
  }
</style>
