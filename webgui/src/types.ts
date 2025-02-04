export interface LaserHeadInfo {
    serial: string;
    type: string;
    hours: string;
    board_revision: string;
    dio_status: string;
}

export interface LaserSignals {
    power: number[];
    powerSetpoint: number[];
    lddCurrent: number[];
    lddCurrentLimit: number[];
    mainTemperature: number[];
    shgTemperature: number[];
    brfTemperature: number[];
    etalonTemperature: number[];
}

export interface LaserFlags {
    interlock: boolean;
    keySwitch: boolean;
    softwareSwitch: boolean;
    remoteControl: boolean;
    analogInput: boolean;
}


export interface Laser {
    headInfo: LaserHeadInfo;
    signals: LaserSignals;
    flags: LaserFlags;
}

export interface Message {
    type: string;
    request_id?: string;
}

export interface SignalsMessage extends Message {
    type: 'signals';
    data: { [key: string]: LaserSignals };
}

export interface FlagsMessage extends Message {
    type: 'flags';
    data: { [key: string]: LaserFlags };
}
