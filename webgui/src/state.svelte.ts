import * as d3 from 'd3'
const API_ENDPOINT = new URL('http://localhost:8000/api/genesis-mx/')

const getWsEndpoint = (url: URL) => {
    const wsUrl = new URL(url)
    wsUrl.protocol = 'ws'
    return wsUrl
}

export interface LaserHeadInfo {
    serial: string;
    type: string;
    hours: string;
    board_revision: string;
    dio_status: string;
}

interface LaserSignalValues {
    power: number;
    powerSetpoint: number;
    lddCurrent: number;
    lddCurrentLimit: number;
    mainTemperature: number;
    shgTemperature: number;
    brfTemperature: number;
    etalonTemperature: number;
}

export interface LaserFlags {
    interlock: boolean;
    keySwitch: boolean;
    softwareSwitch: boolean;
    remoteControl: boolean;
    analogInput: boolean;
}

interface LaserData {
    head: LaserHeadInfo;
    flags: LaserFlags;
    signals: LaserSignalValues;
}
export interface Message {
    type: string;
    request_id?: string;
    data?: any;
}
export interface SignalsMessage extends Message {
    type: 'signals';
    data: { [key: string]: LaserSignalValues };
}

export interface FlagsMessage extends Message {
    type: 'flags';
    data: { [key: string]: LaserFlags };
}


export class Laser {
    static readonly MAX_SIGNAL_LENGTH = 500;
    head: LaserHeadInfo
    power = $state<number[]>([]);
    powerSetpoint = $state<number[]>([]);
    lddCurrent = $state<number[]>([]);
    lddCurrentLimit = $state<number[]>([]);
    mainTemperature = $state<number[]>([]);
    shgTemperature = $state<number[]>([]);
    brfTemperature = $state<number[]>([]);
    etalonTemperature = $state<number[]>([]);
    flags = $state<LaserFlags>({} as LaserFlags);
    powerLimit: number;
    constructor (head: LaserHeadInfo, flags: LaserFlags, powerLimit: number = 10) {
        this.head = head
        this.flags = flags
        this.powerLimit = powerLimit;
    }

    sendCommand = (command: string, value: number | string | boolean | undefined = undefined) => {
        const endpoint = new URL(command, API_ENDPOINT)
        endpoint.searchParams.set('serial', this.head.serial)
        value !== undefined && (endpoint.searchParams.set('value', value.toString()))
        fetch(endpoint, { method: 'PUT' });
    }
    updateSignals = (signals: LaserSignalValues) => {
        Object.entries(signals).forEach(([key, value]) => {
            const signal = this[key as keyof LaserSignalValues];
            if (signal.length >= Laser.MAX_SIGNAL_LENGTH) {
                signal.shift();
            }
            signal.push(value);
        });
    }
    enable = () => this.sendCommand('enable');
    disable = () => {
        if (!this.flags.softwareSwitch) return;
        if (!this.flags.remoteControl) {
            this.sendCommand('remote', true);
        }
        this.sendCommand('disable')
    }
    setPower = (power: number) => this.sendCommand('power', power);
    toggleRemoteControl = () => {
        if (this.flags.remoteControl) {
            this.sendCommand('remote', false);
        } else {
            this.sendCommand('remote', true);
        }
    }
}


export class GenesisMXState {
    private socket: WebSocket | undefined
    lasers = $state<{ [key: string]: Laser }>({})
    isRunning = $state(false)
    _powerLimit: number = 10;

    init = async () => {
        const res = await fetch(API_ENDPOINT)
        if (!res.ok) throw new Error('Failed to fetch lasers')
        const laserData: LaserData[] = await res.json()
        laserData.forEach((data) => {
            const laser = new Laser(data.head, data.flags, this.powerLimit);
            laser.updateSignals(data.signals)
            this.lasers[data.head.serial] = laser
        })
        this.socket = new WebSocket(getWsEndpoint(API_ENDPOINT));
        this.socket.onmessage = this.handleSocketMessage;
        this.isRunning = true
        return this
    }
    start = () => {
        this.isRunning = true
        // this.socket?.send(JSON.stringify({ type: 'start' }));
    }
    get powerLimit() {
        return this._powerLimit;
    }

    set powerLimit(value: number) {
        this._powerLimit = value;
        Object.values(this.lasers).forEach((laser) => {
            laser.powerLimit = value;
        });
    }

    stop = () => {
        Object.values(this.lasers).forEach((laser) => {
            if (!laser.flags.remoteControl) laser.toggleRemoteControl();
            laser.setPower(0);
            laser.disable();
        });
        this.socket?.close();
        this.socket = undefined;
        this.lasers = {};
        this.isRunning = false;
    }

    handleSocketMessage = (event: MessageEvent) => {
        const message = JSON.parse(event.data) as Message;
        switch (message.type) {
            case 'signals':
                const signalsMessage = message.data as SignalsMessage;
                for (const [serial, signals] of Object.entries(signalsMessage)) {
                    if (!(serial in this.lasers)) {
                        console.warn('Laser not found:', serial);
                        continue;
                    }
                    this.lasers[serial].updateSignals(signals);
                }
                break;
            case 'flags':
                const flagsMessage = message.data as FlagsMessage;
                for (const [serial, flags] of Object.entries(flagsMessage)) {
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

    const svg = d3.select(node);
    const margin = { top: 20, right: 20, bottom: 25, left: 45 };

    const draw = () => {

        svg.selectAll('*').remove();
        const width = container.clientWidth;
        const height = container.clientHeight;

        svg.attr('viewBox', [0, 0, width, height]).attr('class', 'daq-chart').attr('width', width).attr('height', height);

        const getYDomain = () => {
            const MIN_RANGE = laser.powerLimit;
            const min = 0;
            const max = Math.max(d3.max(laser.powerSetpoint) ?? 0, d3.max(laser.power) ?? 0);
            const range = max - min;
            // get the closest multiple of MIN_RANGE that is greater than range
            const domainMax = Math.ceil(range / MIN_RANGE) * MIN_RANGE;
            return [min, domainMax];
        }


        const xScale = d3.scaleLinear()
            .domain([0, Laser.MAX_SIGNAL_LENGTH])
            .range([0, width - margin.left - margin.right]);

        const yScale = d3.scaleLinear()
            .domain(getYDomain())
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

        // Area + Line generators
        const area = d3.area<number>()
            .x((d, i) => xScale(i))
            .y0(d => yScale(0))
            .y1((d) => yScale(d));

        const line = d3.line<number>().x((d, i) => xScale(i)).y((d) => yScale(d));

        const g = svg.append('g').attr('transform', `translate(${ margin.left },${ margin.top })`);

        // 1) POWER as an area (fill +  stroke on top)

        // Area fill
        g.append('path')
            .datum(laser.power)
            .attr('fill', 'var(--cyan-400)')
            .attr('fill-opacity', 0.2)
            .attr('stroke', 'none')
            .attr('d', area);

        // Outline for the power area
        g.append('path')
            .datum(laser.power)
            .attr('fill', 'none')
            .attr('stroke', 'var(--cyan-400)')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 1)
            .attr('d', line);

        // 2) POWER SETPOINT as a simple line
        g.append('path')
            .datum(laser.powerSetpoint)
            .attr('fill', 'none')
            .attr('stroke', 'var(--yellow-400)')
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 1)
            .attr('d', line);

    }
    $effect(() => {
        draw();
    });
    const ro = new ResizeObserver(() => {
        draw();
    });
    ro.observe(container);
}
