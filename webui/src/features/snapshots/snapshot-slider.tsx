import { useEffect, useRef, useState } from 'react';
import './snapshot-slider.scss';
import { TimelapseSnapshot } from '../../models/snapshot';
import { UIState } from '@/models/ui-state';

type Props = {
    snapshots: TimelapseSnapshot[];
    onSelect: (snapshot: TimelapseSnapshot) => void;
}

export const SnapshotSlider = ({ snapshots, onSelect }: Props) => {
    const [startCommit, setStart] = useState(0);
    const [endCommit, setEnd] = useState(100);
    const [isDragging, setIsDragging] = useState(false);

    const sliderRef = useRef(null);

    useEffect(() => {
        const sub = UIState.currentSnapshot.subscribe(snapshot => {
            if (snapshot) {
                const pos = getPosition(snapshot.commit_date);
                setStart(pos);
            }
        });
        return () => sub.unsubscribe();
    }, []);

    const min = snapshots.map(s => s.commit_date).reduce((a, b) => Math.min(a, b));
    const max = snapshots.map(s => s.commit_date).reduce((a, b) => Math.max(a, b));
    const getPosition = (time: number) => (time - min) / (max - min) * 100;

    const commitDots = snapshots.map(s => {
        const style = { left: `${getPosition(s.commit_date)}%` };
        return <div className='snapshot' style={style} key={s.commit_sha}>
            <div className='dot'></div>
            {/* <div className='label'>{commit.date.toLocaleTimeString()}</div> */}
        </div>;
    });


    const onSliderMouseDown = (event: React.MouseEvent<HTMLDivElement, MouseEvent>, type: 'start' | 'end') => {
        event.preventDefault();
        setIsDragging(true);
        const setPosition = type === 'start' ? setStart : setEnd;

        if (sliderRef) {
            const handlePos = (sliderRef.current as any).getBoundingClientRect().left;
            const width = (sliderRef.current as any).getBoundingClientRect().width;
            let current = -1;

            const onMouseMove = (e: MouseEvent) => {
                e.preventDefault();
                const mousePos = e.pageX;
                const pos = (mousePos - handlePos) / width * 100;
                current = Math.min(Math.max(0, pos), 100);
                setPosition(current);
            };

            const onMouseUp = (e: MouseEvent) => {
                e.preventDefault();
                window.removeEventListener('mousemove', onMouseMove);
                window.removeEventListener('mouseup', onMouseUp);

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

                if (closestDistance !== undefined)
                    setPosition(closestDistance);

                if (closestSnapshot)
                    UIState.setCurrentSnapshot(closestSnapshot.commit_sha);


                setIsDragging(false);
            };

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        }
    };


    return <div className='slider-container'>
        <div className='slider' ref={sliderRef}>

            <div className='line'></div>
            {commitDots}

            <div className={'snapshot interactive' + (isDragging ? ' dragging' : '')} style={{ 'left': `${startCommit}%` }} onMouseDown={(e) => onSliderMouseDown(e, 'start')}>
                <div className='dot'></div>
            </div>

            {/* <div className={'commit interactive' + (isDragging ? ' dragging' : '')} style={{ 'left': `${endCommit}%` }} onMouseDown={(e) => onSliderMouseDown(e, 'end')}>
                <div className='dot'></div>
            </div> */}

        </div>
    </div>;
};
