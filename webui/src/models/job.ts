// Mirrors `Job.to_dict()` in `tex_timelapse/jobs.py`. A job tracks one
// asynchronous project render, created by `POST /api/projects/<name>/jobs`
// and polled/cancelled via `/api/jobs/<id>`. `stage_progress` is 0..1 within
// the current `stage`; combine the two for an overall progress readout.
export type TimelapseJobStatus = 'running' | 'completed' | 'failed' | 'cancelled';

export type TimelapseJob = {
    'id': string;
    'project': string;
    'output': string;
    'status': TimelapseJobStatus;
    'stage': string;
    'stage_length': number;
    'stage_progress': number;
    'error': string;
}
