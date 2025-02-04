<script lang="ts">
  interface DeliminatedInputProps {
    value: number;
    onChange?: (value: number) => void;
    min?: number;
    max?: number;
    step?: number;
  }

  let {
    value = $bindable(),
    onChange,
    min,
    max,
    step,
  }: DeliminatedInputProps = $props();

  let textInput: HTMLInputElement;

  function enforceDelimination(value: number) {
    if (min !== undefined) {
      if (value < min) {
        return min;
      } else if (step) {
        const distanceFromMin = value - min;
        const numSteps = Math.round(distanceFromMin / step);
        value = min + numSteps * step;
      }
    }
    if (max !== undefined && value > max) return max;
    return value;
  }

  function updateValue(e: Event) {
    const target = e.target as HTMLInputElement;
    let newValue = Number(target.value);
    if (isNaN(newValue)) return;
    newValue = enforceDelimination(newValue);
    textInput.value = newValue.toString();
    return newValue;
  }

  function handleValueChange(e: Event) {
    const newValue = updateValue(e);
    onChange && newValue && onChange(newValue);
  }
</script>

<div class="deliminated-input">
  <input
    type="text"
    {value}
    onchange={handleValueChange}
    bind:this={textInput}
  />
  <input
    type="range"
    {min}
    {max}
    {step}
    {value}
    oninput={updateValue}
    onchange={handleValueChange}
  />
</div>

<style>
  .deliminated-input {
    --hover-color: var(--zinc-600);
    --transition: var(--transition-duration, 0.3s) ease-in-out;

    --thumb-size: 0.75rem;
    --slider-thickness: calc(var(--thumb-size) * 1.5);
    --track-thickness: calc(var(--thumb-size) * 0.5);
    /* --track-bg: var(--zinc-800); */

    /* --border-color: var(--zinc-800); */
    --track-bg: var(--border-color, var(--zinc-800));
    --border: 1px solid var(--track-bg);

    display: flex;
    flex-direction: column;
    background-color: var(--zinc-900);
    padding-bottom: calc((0.75rem - 0.375rem) * 0.5);

    input[type="text"] {
      width: 100%;
      margin-inline: auto;
      text-align: center;
      font-family: monospace;
      font-size: var(--font-sm);
      color: var(--zinc-400);
      padding-block: 0.25rem;
      background-color: var(--bg-color, var(--zinc-900));
      border: var(--border);
      border-bottom: none;
      transition: all var(--transition);
      outline: none;
    }

    input[type="range"] {
      /* style the track */
      -webkit-appearance: none;
      appearance: none;
      outline: none;
      width: 100%;
      height: var(--track-thickness);
      background-color: var(--track-bg);
      border-left: var(--border);
      border-right: var(--border);

      transition: all var(--transition);
      /* style the thumb */
      &::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: var(--thumb-size);
        height: var(--thumb-size);
        background-color: var(--thumb-color, var(--zinc-500));
        opacity: 0.75;
        border-radius: 50%;
        cursor: pointer;
        transition: all var(--transition);
      }

      &:hover,
      &:focus,
      &:focus-within {
        &::-webkit-slider-thumb {
          background-color: var(
            --thumb-hover-color,
            var(--thumb-color, var(--zinc-400))
          );
        }
      }
    }

    &:hover,
    &:focus,
    &:focus-within {
      --track-bg: var(--border-hover-color, var(--zinc-700));

      input[type="range"] {
        &::-webkit-slider-thumb {
          opacity: 1;
        }
      }
    }
  }
</style>
