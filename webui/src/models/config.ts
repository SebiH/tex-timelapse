export type TimelapseConfig = {
    rows: number;
    columns: number;
    videoscale: number;
    framerate: number;

    blur: number;
    highlightChanges: boolean;

    useMultithreading: boolean;
    workers: number;

    startCommit: string;
    endCommit: string;
    // # startDate: Date;
    // # endDate: Date;


    crop: boolean;
    cropTwoPage: boolean;
    cropLeft: number;
    cropRight: number;
    cropTop: number;
    cropBottom: number;
    cropAltLeft: number;
    cropAltRight: number;
    cropAltTop: number;
    cropAltBottom: number;

    latexCmd: string;

    overleafProjectId: string;
    overleafAuthToken: string;
}
