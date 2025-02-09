<script lang="ts">
  import LaserLogo from "/laser-logo.svg";
  // Define types based on the FastAPI status response.
  interface PowerStatus {
    value: number | null;
    setpoint: number | null;
  }

  interface DeviceStatus {
    remote_control: boolean | null;
    key_switch: boolean | null;
    interlock: boolean | null;
    software_switch: boolean | null;
    power: PowerStatus;
    temperature: number | null;
    current: number | null;
    mode: number | null;
    alarms: string[] | null;
  }

  let devices = $state<string[]>([]);
  let statuses = $state<Record<string, DeviceStatus | null>>({});
  let error = $state<string | null>(null);

  const API_BASE: string = "http://localhost:8000/api";

  async function fetchDevices(): Promise<string[]> {
    const res = await fetch(`${API_BASE}/devices`);
    if (!res.ok) {
      throw new Error("Failed to fetch devices.");
    }
    devices = await res.json();
    if (devices.length > 0) {
      devices.forEach((serial) => fetchStatus(serial));
    }
    return devices;
  }

  async function fetchStatus(serial: string): Promise<void> {
    invalidateStatus(serial);
    try {
      const res = await fetch(`${API_BASE}/device/${serial}/status`);
      if (!res.ok) {
        throw new Error(`Failed to fetch status for device ${serial}.`);
      }
      // const status = await res.json();
      // if (status) {
      //   statuses[serial] = status;
      // }
      await updateStatus(serial, res);
    } catch (err: any) {
      error = err.message;
    }
  }

  function invalidateStatus(serial: string): void {
    const currentStatus = { ...statuses[serial] };
    statuses[serial] = null;
  }

  async function updateStatus(
    serial: string,
    response: Response
  ): Promise<void> {
    const newStatus = await response.json();
    if (newStatus) {
      statuses[serial] = newStatus;
    }
  }

  async function sendLaserCommand(
    serial: string,
    command: string
  ): Promise<void> {
    const res = await fetch(`${API_BASE}/device/${serial}/${command}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Failed to ${command} device ${serial}.`);
    }
    updateStatus(serial, res);
  }

  async function enableLaser(serial: string): Promise<void> {
    invalidateStatus(serial);
    await sendLaserCommand(serial, "enable");
  }

  async function disableLaser(serial: string): Promise<void> {
    invalidateStatus(serial);
    await sendLaserCommand(serial, "disable");
  }

  async function setLaserPower(serial: string, power: number): Promise<void> {
    invalidateStatus(serial);
    const res = await fetch(`${API_BASE}/device/${serial}/power`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ power }),
    });
    if (!res.ok) {
      throw new Error(`Failed to set power for device ${serial}.`);
    }
    await updateStatus(serial, res);
  }
  function handleSetLaserPowerInput(e: Event): void {
    const input = e.target as HTMLInputElement;
    const serial = input.dataset.serial;
    if (serial) {
      const value = Math.min(
        Math.max(parseFloat(input.value), parseInt(input.min)),
        parseInt(input.max)
      );
      input.value = value.toString();
      setLaserPower(serial, value);
    }
  }
</script>

{#snippet reloadIcon()}
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 15 15"
  >
    <path
      fill="currentColor"
      fill-rule="evenodd"
      d="M1.85 7.5c0-2.835 2.21-5.65 5.65-5.65c2.778 0 4.152 2.056 4.737 3.15H10.5a.5.5 0 0 0 0 1h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-1 0v1.813C12.296 3.071 10.666.85 7.5.85C3.437.85.85 4.185.85 7.5s2.587 6.65 6.65 6.65c1.944 0 3.562-.77 4.714-1.942a6.8 6.8 0 0 0 1.428-2.167a.5.5 0 1 0-.925-.38a5.8 5.8 0 0 1-1.216 1.846c-.971.99-2.336 1.643-4.001 1.643c-3.44 0-5.65-2.815-5.65-5.65"
      clip-rule="evenodd"
    />
  </svg>
{/snippet}

{#snippet spinner()}
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
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

{#snippet laserCard(serial: string)}
  <div class="laser-card">
    <div class="header">
      <h2 class="text-md zinc-400">{serial}</h2>
      <button onclick={() => fetchStatus(serial)}>Refresh</button>
    </div>
    <div class="status">
      {#if statuses[serial]}
        <pre>{JSON.stringify(statuses[serial], null, 2)}</pre>
      {:else}
        <div>{@render spinner()}</div>
      {/if}
      <button onclick={() => fetchStatus(serial)}>
        {@render reloadIcon()}
      </button>
    </div>
    <div class="controls">
      <button class="enable-button" onclick={() => enableLaser(serial)}>
        Enable
      </button>
      <button class="disable-button" onclick={() => disableLaser(serial)}>
        Disable
      </button>
      <input
        type="number"
        data-serial={serial}
        min="0"
        max="100"
        step="1"
        value={statuses[serial]?.power.setpoint}
        disabled={!statuses[serial] || statuses[serial].power.setpoint === null}
        onchange={handleSetLaserPowerInput}
        onclick={(e) => {
          const target = e.target as HTMLInputElement;
          target && target.select();
        }}
      />
    </div>
  </div>
{/snippet}

<main>
  <div class="header">
    <div class="app-name">
      <img src={LaserLogo} class="logo" alt="Laser Logo" />
      <h1>Genesis MX</h1>
    </div>
  </div>
  <section class="laser-cards">
    {#await fetchDevices()}
      <p>Loading devices...</p>
    {:then devices}
      {#if devices.length === 0}
        <p>No devices found.</p>
      {:else}
        {#each devices as laser}
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
    padding: 1rem;
    > .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
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
    border: 1px solid var(--zinc-700);
    border-radius: 4px;
    padding-block-end: var(--padding);
    display: grid;
    grid-template-rows: auto minmax(24rem, 1fr) auto;
    .header {
      padding-inline: var(--padding);
      padding-block: 0.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--zinc-700);
      h2 {
        margin: 0;
      }
      button {
        background-color: var(--zinc-800);
        color: var(--zinc-300);
        border: none;
        padding: 0.5rem;
        border-radius: 4px;
        cursor: pointer;
      }
      button:hover {
        background-color: var(--zinc-700);
      }
    }

    .status {
      padding: 1rem;
      margin: 1rem;
      border: 1px solid var(--zinc-800);
      background-color: var(--zinc-900);
      border-radius: 4px;
      position: relative;
      button {
        position: absolute;
        right: 0.5rem;
        top: 0.5rem;
        color: var(--emerald-400);
        transition: color 0.3s;
        padding: 0.5rem;
        border-radius: 50%;
        &:hover {
          color: var(--yellow-500);
          background-color: var(--zinc-800);
        }
        &:focus-visible {
          outline: none;
        }
      }
    }

    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr 2fr;
      gap: 1rem;
      padding-inline: var(--padding);
      button,
      input {
        color: var(--zinc-50);
        font-size: var(--font-md);
        font-weight: 400;
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid var(--color);
        &:focus-visible {
          outline: none;
        }
      }
      input {
        --color: var(--zinc-600);
        background-color: var(--zinc-900);
        text-align: center;
        transition: border-color 0.3s;
        &:hover,
        &:focus {
          --color: var(--zinc-400);
        }
        &:disabled {
          /* color: transparent; */
          background-color: var(--zinc-900);
          cursor: not-allowed;
          opacity: 0.5;
        }
        &::-webkit-inner-spin-button {
          appearance: none;
        }
      }
      button {
        cursor: pointer;
        background-color: transparent;
        transition: background-color 0.3s;
        &.enable-button {
          --color: var(--lime-700);
        }
        &.disable-button {
          --color: var(--rose-700);
        }
        &:hover {
          background-color: var(--color);
          color: var(--zinc-50);
        }
      }
    }
  }
  .error {
    color: red;
  }
</style>
