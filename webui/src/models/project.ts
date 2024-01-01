import { TimelapseConfig } from './config';
import { TimelapseSnapshot } from './snapshot';

export type TimelapseProject = {
    config: TimelapseConfig;
    snapshots: TimelapseSnapshot[];
}
