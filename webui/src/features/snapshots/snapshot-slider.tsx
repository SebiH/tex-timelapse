import { useEffect, useRef, useState } from 'react';
import './snapshot-slider.scss';
import { TimelapseSnapshot } from '../../models/snapshot';
import { UIState } from '@/models/ui-state';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, MoveLeft, MoveRight } from 'lucide-react';

type Props = {
    snapshots: TimelapseSnapshot[];
    startSnapshot: TimelapseSnapshot;
    endSnapshot?: TimelapseSnapshot;
    mode: 'single' | 'range';
}

const jobs = [
    { name: 'Init Repository' },
    { name: 'Compile LaTeX' },
    { name: 'PDF to Image' },
    { name: 'Assemble Image' }
];

export const SnapshotSlider = ({ snapshots, mode, startSnapshot, endSnapshot }: Props) => {
    const [startCommit, setStart] = useState(0);
    const [endCommit, setEnd] = useState(100);
    const [isDragging, setIsDragging] = useState(false);

    useEffect(() => {
        const sub = UIState.currentSnapshot.subscribe(snapshot => {
            if (snapshot && mode === 'single' && !isDragging) {
                const pos = getPosition(snapshot.commit_date);
                setStart(pos);
            }
        });
        return () => sub.unsubscribe();
    }, []);

    const sliderRef = useRef(null);

    const selectSnapshot = (snapshot: TimelapseSnapshot) => {
        UIState.setCurrentSnapshot(snapshot.commit_sha);
    };

    const min = snapshots.map(s => s.commit_date).reduce((a, b) => Math.min(a, b));
    const max = snapshots.map(s => s.commit_date).reduce((a, b) => Math.max(a, b));
    const getPosition = (time: number) => (time - min) / (max - min) * 100;

    const commitDots = snapshots.map(s => {
        const style = { left: `${getPosition(s.commit_date)}%`, 'backgroundColor': '#D8DEE9' };

        for (const job of jobs) {
            if (s.status[job.name] === 'In Progress') {
                style['backgroundColor'] = '#EBCB8B';
            } else if (s.status[job.name] === 'Completed') {
                style['backgroundColor'] = '#A3BE8C';
            } else if (s.status[job.name] === 'Failed') {
                style['backgroundColor'] = '#BF616A';
            }
        }

        const classNames = `snapshot ${mode === 'single' && 'interactive'} ${startSnapshot === s && 'selected'}`;
        return <div className={classNames} style={style} key={s.commit_sha} onClick={() => selectSnapshot(s)}>
            <div className='dot'></div>
            {/* <div className='label'>{commit.date.toLocaleTimeString()}</div> */}
        </div>;
    });


    const onSliderMouseDown = (event: React.MouseEvent<HTMLDivElement, MouseEvent>, type: 'start' | 'end') => {
        event.preventDefault();
        setIsDragging(true);
        const setPosition = type === 'start' ? setStart : setEnd;


        const setClosestSnapshot = (current: number, snap: boolean) => {
            // find closest snapshot
            let closestDistance: number | undefined;
            let closestSnapshot: TimelapseSnapshot | undefined;
            for (const snapshot of snapshots) {
                const pos = getPosition(snapshot.commit_date);
                if (closestDistance === undefined || Math.abs(pos - current) < Math.abs(closestDistance - current)) {
                    closestDistance = pos;
                    closestSnapshot = snapshot;
                }
            }

            if (closestDistance !== undefined && snap)
                setPosition(closestDistance);

            if (closestSnapshot)
                UIState.setCurrentSnapshot(closestSnapshot.commit_sha);
        };

        if (sliderRef) {
            const handlePos = (sliderRef.current as any).getBoundingClientRect().left;
            const width = (sliderRef.current as any).getBoundingClientRect().width;
            let current = -1;

            const onMouseMove = (e: MouseEvent) => {
                e.preventDefault();
                const mousePos = e.pageX - 10; // half the width of the handle
                const pos = (mousePos - handlePos) / width * 100;
                current = Math.min(Math.max(0, pos), 100);
                setClosestSnapshot(current, false);
                setPosition(current);
            };

            // initialising current position in case mouse doesn't move
            onMouseMove(event.nativeEvent);

            const onMouseUp = (e: MouseEvent) => {
                e.preventDefault();
                window.removeEventListener('mousemove', onMouseMove);
                window.removeEventListener('mouseup', onMouseUp);

                setClosestSnapshot(current, true);
                setIsDragging(false);
            };

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        }
    };

    const selectNext = () => {
        // assumes snapshots are sorted by date
        const currentIndex = snapshots.findIndex(s => s === startSnapshot);
        if (currentIndex < snapshots.length - 1) {
            UIState.setCurrentSnapshot(snapshots[currentIndex + 1].commit_sha);
        }
    };

    const selectPrev = () => {
        // assumes snapshots are sorted by date
        const currentIndex = snapshots.findIndex(s => s === startSnapshot);
        if (currentIndex > 0) {
            UIState.setCurrentSnapshot(snapshots[currentIndex - 1].commit_sha);
        }
    };

    return <div className='selection-container'>

        <Button variant='ghost' className='h-full' onClick={selectPrev.bind(this)}>
            <ChevronLeft />
        </Button>

        <div className='slider-container'>

            <div className='slider' ref={sliderRef}>

                <div className='line'></div>
                {commitDots}

                <div className={'snapshot interactive slider' + (isDragging ? ' dragging' : '')} style={{ 'left': `${startCommit}%` }} onMouseDown={(e) => onSliderMouseDown(e, 'start')}>
                    <div className='dot'></div>
                </div>

                {/* <div className={'commit interactive' + (isDragging ? ' dragging' : '')} style={{ 'left': `${endCommit}%` }} onMouseDown={(e) => onSliderMouseDown(e, 'end')}>
                    <div className='dot'></div>
                </div> */}

            </div>
        </div>

        <Button variant='ghost' className='h-full' onClick={selectNext.bind(this)}>
            <ChevronRight />
        </Button>
    </div>;
};
