import { LoaderFunctionArgs, useLoaderData } from 'react-router-dom';
import SnapshotSlider from '../features/snapshot-slider/snapshot-slider';
import { useEffect, useState } from 'react';

import './Project.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCube, faCubes } from '@fortawesome/free-solid-svg-icons';
import { TimelapseProject } from '../models/project';
import { TimelapseSnapshot } from '../models/snapshot';
import { socket } from '../socketio';

export async function loader({ params }: LoaderFunctionArgs<{ projectName: string }>) {
    return await fetch(`/api/projects/${params.projectName}`);
}

const Project = () => {
    const project = useLoaderData() as TimelapseProject;

    useEffect(() => {
        const onData = (data: any) => {
            console.log(data);
        };
        socket.on('log', onData);

        return () => {
            socket.off('log', onData);
        };
    }, []);

    if (!project) {
        return <div>Loading... / Show new project site</div>;
    }

    const [ selectedCommit, setSelectedCommit ] = useState<TimelapseSnapshot | null>(null);

    console.log(selectedCommit);

    let commitPages = <></>;
    if (selectedCommit && selectedCommit.status['PDF to Image'] === 'Completed') {
        const pages = selectedCommit.pages.map(p => `/api/projects/sample/snapshot/${selectedCommit.commit_sha}/image/${p}`);

        commitPages = <div className='imgContainer'>
            { pages.map(p => <img src={p} alt='page' key={p} />) }
        </div>;
    }

    let snapshotStatus = <></>;
    if (selectedCommit) {
        snapshotStatus = <div>
            <code><pre>{ JSON.stringify(selectedCommit, null, 4) }</pre></code>
        </div>;
    }


    let pdfPreview = <></>;

    if (selectedCommit && selectedCommit.status['Compile LaTeX'] === 'Completed') {
        pdfPreview = <div className='pdfPreview'>
            <embed src={ `http://localhost:5000/api/projects/sample/snapshot/${selectedCommit.commit_sha}/pdf` } width="500" height="375" type="application/pdf"></embed>
        </div>;
    }

    let errorMessages = <></>;

    if (selectedCommit && selectedCommit.error) {
        errorMessages = <div className='errorMessages'>
            { selectedCommit.error }
        </div>;
    }

    const runSnapshot = async () => {
        if (!selectedCommit) {
            alert('Please select a snapshot first.');
            return;
        }

        const request = await fetch(`/api/projects/${project.name}/snapshot/${selectedCommit.commit_sha}/run`);
        const response = await request.json();

        if (response.error) {
            console.warn(response.error);
        } else {
            project.snapshots = [
                ...project.snapshots.filter(s => s.commit_sha !== selectedCommit.commit_sha),
                response.snapshot
            ];
            setSelectedCommit(response.snapshot);
        }
    };

    return (
        <div>
            <div className='main-btn'>
                <div className='btn-icon'>
                    <FontAwesomeIcon icon={faCubes} />
                </div>
                <div className='btn-content'>
                    Run
                </div>
            </div>

            <div className='main-btn' onClick={runSnapshot.bind(this)}>
                <div className='btn-icon'>
                    <FontAwesomeIcon icon={faCube} />
                </div>
                <div className='btn-content'>
                    Compile this snapshot
                </div>
            </div>

            <br/>
            <hr/>

            <SnapshotSlider snapshots={project.snapshots} onSelect={setSelectedCommit} />

            {commitPages}
            {pdfPreview}
            {errorMessages}
            {snapshotStatus}
        </div>
    );
};

export default Project;