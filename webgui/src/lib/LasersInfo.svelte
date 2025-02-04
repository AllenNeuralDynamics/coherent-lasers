<script lang="ts">
  import type { Laser } from "../types";

  let { lasers }: { lasers: Record<string, Laser> } = $props();
</script>

<div class="laser-info">
  {#each Object.entries(lasers) as [serial, laser]}
    <div>
      <p>Serial: {serial}</p>
      <pre>{JSON.stringify(laser, null, 2)}</pre>
    </div>
  {/each}
</div>

<style>
  .laser-info {
    --vertical-spacing: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: var(--vertical-spacing);
    overflow-y: auto;
    color: var(--zinc-300);
    border-inline-start: 1px solid var(--zinc-700);
    background-color: var(--zinc-800);
    > div {
      padding-inline: 1rem;
      padding-block: 0.5rem;
      border-block-end: 2px solid var(--zinc-700);
      /* margin-block: 0.5rem; */
    }
    p {
      font-size: var(--font-sm);
      padding-block: 0.5rem;
      font-weight: 500;
      color: var(--zinc-400);
    }
  }
</style>
