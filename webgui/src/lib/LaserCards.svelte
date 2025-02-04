<script lang="ts">
  import { type Laser } from "../state.svelte";
  import LaserCard from "./LaserCard.svelte";

  let { lasers }: { lasers: Record<string, Laser> } = $props();
</script>

<div class="laser-cards">
  {#each Object.values(lasers) as laser}
    <LaserCard {laser} />
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
</style>
