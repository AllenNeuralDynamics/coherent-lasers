import type { Laser, Message, SignalsMessage, FlagsMessage } from './types'
import * as d3 from 'd3'
const API_ENDPOINT = new URL('http://localhost:8000/api/genesis-mx')

const getWsEndpoint = (url: URL) => {
    const wsUrl = new URL(url)
    wsUrl.protocol = 'ws'
    return wsUrl
}

export class GenesisMXState {
    socket: WebSocket;
    lasers = $state<{ [key: string]: Laser }>({})

    constructor () {
        this.socket = new WebSocket(getWsEndpoint(API_ENDPOINT));
        this.socket.onmessage = this.handleSocketMessage;
    }

    init = async () => {
        const res = await fetch(API_ENDPOINT)
        if (!res.ok) throw new Error('Failed to fetch lasers')
        const data: Laser[] = await res.json()
        this.lasers = data.reduce((acc, laser) => {
            acc[laser.headInfo.serial] = laser
            return acc
        }, {} as { [key: string]: Laser })
    }

    sendLaserCommand = (laser: Laser, command: string, value: number | string | undefined = undefined) => {
        const endpoint = new URL(`/${ laser.headInfo.serial }/${ command }`, API_ENDPOINT)
        value && (endpoint.searchParams.set('value', value.toString()))
        fetch(endpoint, { method: 'PUT' });
    }

    enableLaser = (laser: Laser) => this.sendLaserCommand(laser, 'enable');

    disableLaser = (laser: Laser) => this.sendLaserCommand(laser, 'disable');

    setLaserPower = (laser: Laser, power: number) => this.sendLaserCommand(laser, 'power', power);

    handleSocketMessage = (event: MessageEvent) => {
        const message = JSON.parse(event.data) as Message;
        switch (message.type) {
            case 'signals':
                const signalsMessage = message as SignalsMessage;
                for (const [serial, signals] of Object.entries(signalsMessage.data)) {
                    this.lasers[serial].signals = signals;
                }
                break;
            case 'flags':
                const flagsMessage = message as FlagsMessage;
                for (const [serial, flags] of Object.entries(flagsMessage.data)) {
                    this.lasers[serial].flags = flags;
                }
                break;
            default:
                console.error('Unknown message type:', message.type);
        }
    }

}


export const LaserPowerChart = (node: SVGSVGElement, laser: Laser) => {
    const container = node.parentElement ?? node;
    const numXPoints = 100;

    const svg = d3.select(node);
    const margin = { top: 5, right: 20, bottom: 10, left: 50 };

    const draw = () => {

        svg.selectAll('*').remove();
        const width = container.clientWidth;
        const height = container.clientHeight;

        svg.attr('viewBox', [0, 0, width, height]).attr('class', 'daq-chart').attr('width', width).attr('height', height);

        const xScale = d3.scaleLinear()
            .domain([0, numXPoints])
            .range([0, width - margin.left - margin.right]);

        const yScale = d3.scaleLinear()
            .domain([-100 * 1.1, 1000 * 1.1])
            .range([height - margin.top - margin.bottom, 0]);

        const axes = svg.append('g').attr('class', 'axes daq-axes');
        const xTicks = d3.axisBottom(xScale)
            .ticks(width / 60).tickSize(-height + margin.top + margin.bottom).tickSizeOuter(0).tickPadding(10)
            .tickFormat(() => '');
        axes.append('g')
            .attr('class', 'grid')
            .attr('transform', `translate(${ margin.left },${ height - margin.bottom - 1 })`)
            .call(xTicks);
        axes.append('g')
            .attr('class', 'grid')
            .attr('transform', `translate(${ margin.left }, ${ margin.top })`)
            .call(d3.axisLeft(yScale).tickSize(-width + margin.left + margin.right).tickPadding(10));

        const line = d3.line<number>().x((d, i) => xScale(i)).y((d) => yScale(d));

        const g = svg.append('g').attr('transform', `translate(${ margin.left },${ margin.top })`);

        g.append('path')
            .datum(laser.signals.power)
            .attr('fill', 'none')
            .attr('stroke', 'steelblue')
            .attr('stroke-width', 1.5)
            .attr('d', line);

        g.append('path')
            .datum(laser.signals.powerSetpoint)
            .attr('fill', 'none')
            .attr('stroke', 'var(--yellow-400)')
            .attr('stroke-width', 1.0)
            .attr('d', line);
    }
    draw();
    const ro = new ResizeObserver(() => {
        draw();
    });
    ro.observe(container);
}
