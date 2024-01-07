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
        const a = [1, 2, 3, 4, 5];
        const pages = a.map(n => `/api/projects/test/snapshot/${selectedCommit.commit_sha}/image/page-0${n}.png`);

        commitPages = <div className='imgContainer'>
            { pages.map(p => <img src={p} alt='page' key={p} />) }
        </div>;
    }

    let pdfPreview = <></>;

    if (selectedCommit && selectedCommit.status['Compile LaTeX'] === 'Completed') {
        pdfPreview = <div className='pdfPreview'>
            <embed src={ `http://localhost:5000/api/projects/test/snapshot/${selectedCommit.commit_sha}/pdf` } width="500" height="375" type="application/pdf"></embed>
        </div>;
    }

    let errorMessages = <></>;

    if (selectedCommit && selectedCommit.error) {
        errorMessages = <div className='errorMessages'>
            { selectedCommit.error }
        </div>;
    }

    const runSnapshot = async () => {
        const request = await fetch(`/api/projects/${project.name}/snapshot/${selectedCommit?.commit_sha}/run`);
        const response = await request.json();

        if (response.error) {
            console.warn(response.error);
        } else if (selectedCommit) {
            selectedCommit.status = {
                'PDF to Image': 'Completed',
                'Compile LaTeX': 'Completed'
            };
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
        </div>
    );
};

export default Project;