import * as d3 from "d3";
import { MAX_HISTORY_LENGTH, type Laser } from "./laser.svelte";

interface LaserChartProps {
    laser: Laser;
    getPowerRange: () => [number, number];
}

export const laserPowerChart = (node: SVGElement, { laser, getPowerRange }: LaserChartProps) => {
    const container = node.parentElement ?? node;
    const svg = d3.select(node);
    const margin = { top: 20, right: 10, bottom: 25, left: 45 };

    const draw = () => {
        svg.selectAll("*").remove();
        const width = container.clientWidth;
        const height = container.clientHeight;

        svg
            .attr("viewBox", [0, 0, width, height])
            .attr("class", "daq-chart")
            .attr("width", width)
            .attr("height", height);

        const xScale = d3
            .scaleLinear()
            .domain([0, MAX_HISTORY_LENGTH])
            .range([0, width - margin.left - margin.right]);

        const yScale = d3
            .scaleLinear()
            .domain(getPowerRange())
            .range([height - margin.top - margin.bottom, 0]);

        const axes = svg.append("g").attr("class", "axes daq-axes");
        const xTicks = d3
            .axisBottom(xScale)
            .ticks(width / 60)
            .tickSize(-height + margin.top + margin.bottom)
            .tickSizeOuter(0)
            .tickPadding(10)
            .tickFormat(() => "");
        axes
            .append("g")
            .attr("class", "grid")
            .attr(
                "transform",
                `translate(${ margin.left },${ height - margin.bottom - 1 })`
            )
            .call(xTicks);
        axes
            .append("g")
            .attr("class", "grid")
            .attr("transform", `translate(${ margin.left }, ${ margin.top })`)
            .call(
                d3
                    .axisLeft(yScale)
                    .tickSize(-width + margin.left + margin.right)
                    .tickPadding(10)
            );

        // Area + Line generators
        const area = d3
            .area<number>()
            .x((d, i) => xScale(i))
            .y0((d) => yScale(0))
            .y1((d) => yScale(d));

        const line = d3
            .line<number>()
            .x((d, i) => xScale(i))
            .y((d) => yScale(d));

        const g = svg
            .append("g")
            .attr("transform", `translate(${ margin.left },${ margin.top })`);

        // 1) POWER as an area (fill +  stroke on top)

        // Area fill
        g.append("path")
            .datum(laser.powerValueData)
            .attr("fill", "var(--cyan-400)")
            .attr("fill-opacity", 0.2)
            .attr("stroke", "none")
            .attr("d", area);

        // Outline for the power area
        g.append("path")
            .datum(laser.powerValueData)
            .attr("fill", "none")
            .attr("stroke", "var(--cyan-400)")
            .attr("stroke-width", 1)
            .attr("stroke-opacity", 1)
            .attr("d", line);

        // 2) POWER SETPOINT as a simple line
        g.append("path")
            .datum(laser.powerSetpointData)
            .attr("fill", "none")
            .attr("stroke", "var(--yellow-400)")
            .attr("stroke-width", 2)
            .attr("stroke-opacity", 1)
            .attr("d", line);
    };
    $effect(() => {
        draw();
    });
    const ro = new ResizeObserver(() => {
        draw();
    });
    ro.observe(container);
};


// Alternatively, this action could be used to animate the chart. Not yet working reliably.

export function laserPowerChartAnimate(node: SVGElement, { laser, getPowerRange }: LaserChartProps) {

    const container = node.parentElement ?? node;
    const margin = { top: 20, right: 10, bottom: 25, left: 45 };

    // Set up the base SVG element.
    const svg = d3.select(node)
        .attr("class", "daq-chart");

    // Group to hold chart elements, translated to account for margins.
    const g = svg.append("g")
        .attr("transform", `translate(${ margin.left },${ margin.top })`);

    // Create and append the three paths that will be updated:
    g.append("path")
        .attr("class", "power-area")
        .attr("fill", "var(--cyan-400)")
        .attr("fill-opacity", 0.2);

    g.append("path")
        .attr("class", "power-line")
        .attr("fill", "none")
        .attr("stroke", "var(--cyan-400)")
        .attr("stroke-width", 1);

    g.append("path")
        .attr("class", "setpoint-line")
        .attr("fill", "none")
        .attr("stroke", "var(--yellow-400)")
        .attr("stroke-width", 2);

    // Create a group for the axes.
    const axesGroup = svg.append("g").attr("class", "axes daq-axes");

    // The updateChart function will recalc dimensions, scales, and update paths.
    function updateChart() {
        // Read container dimensions.
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Update the SVG element's size and viewBox.
        svg
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", `0 0 ${ width } ${ height }`);

        // Define the x scale based on the history length.
        const xScale = d3.scaleLinear()
            .domain([0, MAX_HISTORY_LENGTH])
            .range([0, width - margin.left - margin.right]);

        // Compute a maximum power value.
        const yScale = d3.scaleLinear()
            .domain(getPowerRange())
            .range([height - margin.top - margin.bottom, 0]);

        // Clear and redraw the grid axes.
        axesGroup.selectAll("*").remove();

        const xAxis = d3.axisBottom(xScale)
            .ticks(width / 60)
            .tickSize(-height + margin.top + margin.bottom)
            .tickSizeOuter(0)
            .tickPadding(10)
            .tickFormat(() => "");

        axesGroup.append("g")
            .attr("class", "grid")
            .attr("transform", `translate(${ margin.left },${ height - margin.bottom - 1 })`)
            .call(xAxis);

        const yAxis = d3.axisLeft(yScale)
            .tickSize(-width + margin.left + margin.right)
            .tickPadding(10);

        axesGroup.append("g")
            .attr("class", "grid")
            .attr("transform", `translate(${ margin.left },${ margin.top })`)
            .call(yAxis);

        // Define the area and line generators.
        const area = d3.area<number>()
            .x((d, i) => xScale(i))
            .y0(yScale(0))
            .y1(d => yScale(d));

        const line = d3.line<number>()
            .x((d, i) => xScale(i))
            .y(d => yScale(d));

        // Update the power area with a smooth transition.
        g.select(".power-area")
            .datum(laser.powerValueData)
            .transition()
            .duration(500)
            .attr("d", area);

        // Update the power line path.
        g.select(".power-line")
            .datum(laser.powerValueData)
            .transition()
            .duration(500)
            .attr("d", line);

        // Update the setpoint line path.
        g.select(".setpoint-line")
            .datum(laser.powerSetpointData)
            .transition()
            .duration(500)
            .attr("d", line);
    }

    $effect(() => {
        updateChart();
    });

    const resizeObserver = new ResizeObserver(() => {
        updateChart();
    });
    resizeObserver.observe(container);

    return {

        destroy() {
            resizeObserver.disconnect();
        }
    };
}
