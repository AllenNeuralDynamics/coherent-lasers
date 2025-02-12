<script lang="ts">
  interface DeliminatedInputProps {
    value?: number;
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
    bind:this={textInput}
    onchange={handleValueChange}
    onclick={(e) => {
      const target = e.target as HTMLInputElement;
      target && target.select();
    }}
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

    --base-size: var(--thumb-size, 0.75rem);
    --track-bg: var(--border-color, var(--zinc-800));

    --border: var(--border-size, 1px) solid var(--track-bg);
    --_track-thickness: var(--track-thickness, calc(var(--base-size) * 0.3));

    border-radius: var(--border-radius);
    border: var(--border);
    border-bottom: none;
    position: relative;
    height: calc(var(--height, 100%) + (var(--_track-thickness) * 0.5));
    padding-bottom: var(--base-size);
    border-top-left-radius: var(--border-radius);
    border-top-right-radius: var(--border-radius);

    input[type="text"] {
      width: 100%;
      height: calc(var(--height, 100%) - var(--_track-thickness));
      text-align: center;
      font-family: inherit;
      font-size: inherit;
      color: inherit;
      border: none;
      outline: none;
      background-color: var(--bg-color, transparent);
      transition: all var(--transition);
    }

    input[type="range"] {
      position: absolute;
      bottom: calc(var(--_track-thickness) * 0.5);
      left: 0;
      right: 0;
      /* style the track */
      -webkit-appearance: none;
      appearance: none;
      outline: none;
      height: var(--_track-thickness);
      background-color: var(--track-bg);
      border-radius: 5%;

      transition: all var(--transition);
      /* style the thumb */
      &::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: var(--base-size);
        height: var(--base-size);
        background-color: var(--thumb-color, var(--zinc-500));
        opacity: var(--thumb-opacity, 1);
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
