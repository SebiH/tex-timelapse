import { useRef, useState } from 'react';
import './commit-slider.scss';

const CommitSlider = () => {
    const [ startCommit, setStart ] = useState(0);
    const [ endCommit, setEnd ] = useState(100);
    const [ isDragging, setIsDragging ] = useState(false);

    const sliderRef = useRef(null);

    const commits = [
        { date: new Date('2021-01-01T00:00:00'), sha: '1234567891' },
        { date: new Date('2021-01-01T01:00:00'), sha: '1234567892' },
        { date: new Date('2021-01-01T02:00:00'), sha: '1234567893' },
        { date: new Date('2021-01-01T03:00:00'), sha: '1234567894' },
        { date: new Date('2021-01-01T03:05:00'), sha: '1234567895' },
    ];

    const min = commits.map(c => c.date.getTime()).reduce((a, b) => Math.min(a, b));
    const max = commits.map(c => c.date.getTime()).reduce((a, b) => Math.max(a, b));
    const getPosition = (time: number) => (time - min) / (max - min) * 100;

    const commitDots = commits.map(commit => {
        const style = { left: `${ getPosition(commit.date.getTime()) }%` };
        return <div className='commit' style={style} key={commit.sha}>
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

                // find closest commit
                let closest: any;
                for (const commit of commits) {
                    const pos = getPosition(commit.date.getTime());
                    if (closest === undefined || Math.abs(pos - current) < Math.abs(closest - current)) {
                        closest = pos;
                    }
                }

                if (closest !== undefined)
                    setPosition(closest);

                setIsDragging(false);
            };

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        }
    };


    return <div className='slider-container'>
        <div className='slider' ref={sliderRef}>

            <div className='line'></div>
            { commitDots }
            
            <div className={ 'commit interactive' + (isDragging ? ' dragging' : '') } style={{ 'left': `${startCommit}%` }} onMouseDown={(e) => onSliderMouseDown(e, 'start')}>
                <div className='dot'></div>
            </div>

            <div className={ 'commit interactive' + (isDragging ? ' dragging' : '') } style={{ 'left': `${endCommit}%` }} onMouseDown={(e) => onSliderMouseDown(e, 'end')}>
                <div className='dot'></div>
            </div>

        </div>
    </div>;
};

export default CommitSlider;