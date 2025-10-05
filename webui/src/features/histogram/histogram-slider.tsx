import './histogram-slider.scss';
import { TimelapseSnapshot } from '../../models/snapshot';
import { useEffect } from 'react';
import { Histogram } from './histogram';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronLeft, faChevronRight } from '@fortawesome/free-solid-svg-icons';
import { UIState } from '@/models/ui-state';

type Props = {
    snapshots: TimelapseSnapshot[];
    startSnapshot: TimelapseSnapshot;
    endSnapshot?: TimelapseSnapshot;
    mode: 'single' | 'range';
};

export const HistogramSlider = ({ snapshots, mode, startSnapshot, endSnapshot }: Props) => {
    useEffect(() => {

    }, [snapshots]);

    const handleHistogramClick = (event: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
        const boundingRect = event.currentTarget.getBoundingClientRect();
        const clickX = event.clientX - boundingRect.left;
        const clickRatio = clickX / boundingRect.width;
        const clickedIndex = Math.round(clickRatio * (snapshots.length - 1));
        const clickedSnapshot = snapshots[clickedIndex];
        console.log('Clicked on snapshot:', clickedSnapshot, 'at index:', clickedIndex);

        UIState.setCurrentSnapshot(clickedSnapshot.commit_sha);
    };

    const handlePrevious = () => {
        const currentIndex = snapshots.findIndex(s => s.commit_sha === startSnapshot.commit_sha);
        if (currentIndex > 0) {
            const previousSnapshot = snapshots[currentIndex - 1];
            UIState.setCurrentSnapshot(previousSnapshot.commit_sha);
        }
    };

    const handleNext = () => {
        const currentIndex = snapshots.findIndex(s => s.commit_sha === startSnapshot.commit_sha);
        if (currentIndex < snapshots.length - 1) {
            const nextSnapshot = snapshots[currentIndex + 1];
            UIState.setCurrentSnapshot(nextSnapshot.commit_sha);
        }
    };

    return (
        <div className="histogram-slider-container">
            <button className='flex flex-row gap-2 mr-2' onClick={handlePrevious.bind(this)}>
                <FontAwesomeIcon icon={faChevronLeft} />
            </button>

            <div style={{ cursor: 'pointer', width: '100%' }} onClick={handleHistogramClick.bind(this)}>
                <Histogram snapshots={snapshots}/>
            </div>

            <button className='flex flex-row gap-2 ml-2' onClick={handleNext.bind(this)}>
                <FontAwesomeIcon icon={faChevronRight} />
            </button>

            <div className='slider-indicator' style={{ left: `${(snapshots.indexOf(startSnapshot) / (snapshots.length - 1)) * 100}%` }}>
            </div>
        </div>
    );
};