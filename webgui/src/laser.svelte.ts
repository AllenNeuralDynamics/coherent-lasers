
export const API_BASE: string = "http://localhost:8000/api";
export const MAX_HISTORY_LENGTH = 100;

export interface LaserPower {
    value: number | undefined;
    setpoint: number | undefined;
}

export interface LaserStatus {
    remote_control: boolean | undefined;
    key_switch: boolean | undefined;
    interlock: boolean | undefined;
    software_switch: boolean | undefined;
    power: LaserPower;
    temperature: number | undefined;
    current: number | undefined;
    mode: number | undefined;
    alarms: string[] | undefined;
}

export interface LaserInfo {
    serial: string;
    wavelength: number;
    head_type?: string;
    head_hours?: string;
    head_board?: string;
}

export type Wavelength = 0 | 639 | 561 | 488;

export class Laser {
    serial: string;
    wavelength: Wavelength | undefined;
    status = $state<LaserStatus>({
        remote_control: undefined,
        key_switch: undefined,
        interlock: undefined,
        software_switch: undefined,
        power: { value: undefined, setpoint: undefined },
        temperature: undefined,
        current: undefined,
        mode: undefined,
        alarms: undefined,
    });
    history = $state<LaserStatus[]>([]);
    power = $derived(
        this.status?.power ?? { value: undefined, setpoint: undefined }
    );
    powerValueData = $derived(this.history.map((d) => d.power.value ?? 0));
    powerSetpointData = $derived(
        this.history.map((d) => d.power.setpoint ?? 0)
    );
    enabling = $state(false);
    private ws: WebSocket | null = null;
    connected = $derived(this.ws !== null);

    constructor (serial: string) {
        this.serial = serial;
        this.refreshStatus();
        this.subscribe();
    }

    subscribe() {
        this.ws = new WebSocket(`ws://localhost:8000/ws/device/${ this.serial }`);
        this.refreshInfo();

        this.ws.onopen = () => {
            console.log(`WebSocket connected for device ${ this.serial }`);
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === "power_update") {
                this.status.power = message.data;
            } else if (message.type === "full_status") {
                this.status = message.data;
            }
            this.updateHistory();
        };

        this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        this.ws.onclose = () => {
            console.log(`WebSocket closed for device ${ this.serial }`);
        };
    }

    unsubscribe() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    refreshStatus(): void {
        try {
            console.log("Laser: " + this.serial + " refreshing status");
            fetch(`${ API_BASE }/device/${ this.serial }/status`)
                .then((res) => res.json())
                .then((data) => {
                    this.status = data;
                    this.updateHistory();
                });
        } catch (err: any) {
            console.error(err.message);
        }
    }
    refreshInfo(): void {
        try {
            console.log("Laser: " + this.serial + " refreshing info");
            fetch(`${ API_BASE }/device/${ this.serial }/info`)
                .then((res) => res.json())
                .then((data: LaserInfo) => {
                    if ([0, 639, 561, 488].includes(data.wavelength)) {
                        this.wavelength = data.wavelength as Wavelength;
                    }
                });
        } catch (err: any) {
            console.error(err.message);
        }
    }

    updateHistory() {
        this.history.push({ ...this.status });
        if (this.history.length > MAX_HISTORY_LENGTH + 1) this.history.shift();
    }

    async enable(): Promise<void> {
        this.enabling = true;
        await this.sendCommand("enable");
        this.enabling = false;
    }

    async disable(): Promise<void> {
        await this.sendCommand("disable");
    }

    async sendCommand(command: string): Promise<void> {
        try {
            console.log("Laser: " + this.serial + " sending command: " + command);
            const res = await fetch(
                `${ API_BASE }/device/${ this.serial }/${ command }`,
                {
                    method: "POST",
                }
            );
            if (!res.ok) {
                throw new Error(`Failed to ${ command } device ${ this.serial }.`);
            }
            const status = await res.json();
            this.status = { power: this.status.power, ...status };
            this.updateHistory();
        } catch (err: any) {
            console.error(err.message);
        }
    }

    async setPower(power: number): Promise<void> {
        try {
            const res = await fetch(`${ API_BASE }/device/${ this.serial }/power`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ power }),
            });
            if (!res.ok) {
                throw new Error(`Failed to set power for device ${ this.serial }.`);
            }
        } catch (err: any) {
            console.error(err.message);
        }
    }
}
