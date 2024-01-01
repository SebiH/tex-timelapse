import { TimelapseConfig } from './config';
import { TimelapseSnapshot } from './snapshot';

export type TimelapseProject = {
    name: string;
    config: TimelapseConfig;
    snapshots: TimelapseSnapshot[];
}
