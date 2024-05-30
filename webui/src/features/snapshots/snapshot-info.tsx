import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { BugPlay, Trash } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { TimelapseSnapshot } from '@/models/snapshot';
import { TimelapseProject } from '@/models/project';
import { UIState } from '@/models/ui-state';
import { ToastAction } from '@radix-ui/react-toast';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

import './snapshot-info.scss';

export interface SnapshotInfoProps {
    project: TimelapseProject,
    snapshot: TimelapseSnapshot
}

const jobs = [
    { name: 'Init Repository' },
    { name: 'Compile LaTeX' },
    { name: 'PDF to Image' },
    { name: 'Assemble Image' }
];

export const SnapshotInfo = (props: SnapshotInfoProps) => {
    const { toast } = useToast();

    const resetSnapshot = async () => {
        const commitSha = props.snapshot.commit_sha;
        const success = await UIState.resetSnapshot(commitSha);

        if (success) {
            toast({
                title: 'Success!',
                description: 'Snapshot reset successfully',
                action: <ToastAction altText="View" onClick={() => UIState.setCurrentSnapshot(commitSha)}>Go to snapshot</ToastAction>,
            });
        } else {
            toast({
                title: 'Error',
                description: 'Snapshot could not be reset',
                action: <ToastAction altText="View" onClick={() => UIState.setCurrentSnapshot(commitSha)}>Go to snapshot</ToastAction>,
            });
        }
    };

    const compileSnapshot = async () => {
        const commitSha = props.snapshot.commit_sha;
        const success = await UIState.compileSnapshot(commitSha);

        if (success) {
            toast({
                title: 'Success!',
                description: 'Snapshot compiled successfully',
                action: <ToastAction altText="View" onClick={() => UIState.setCurrentSnapshot(commitSha)}>Go to snapshot</ToastAction>,
            });
        } else {
            toast({
                title: 'Error',
                description: 'Snapshot could not be compiled',
                action: <ToastAction altText="View" onClick={() => UIState.setCurrentSnapshot(commitSha)}>Go to snapshot</ToastAction>,
            });
        }
    };

    const getStatusIndicatorClass = (job: string) => {
        const status = props.snapshot.status[job];
        let className = 'job-status-indicator ';
        if (status === 'Completed') {
            className += 'success';
        } else if (status === 'In Progress') {
            className += 'in-progress';
        } else if (status === 'Failed') {
            className += 'failed';
        }

        return className;
    };

    return <div className='flex flex-col justify-between w-full h-full'>

        <form className='grid w-full items-start gap-6 overflow-y-auto'>

            <fieldset className='grid gap-6 rounded-lg border p-4'>
                <legend className='-ml-1 px-1 text-sm font-medium'>
                    Snapshot Info
                </legend>

                <div className='grid gap-3'>
                    <Label>Date</Label>
                    <Input disabled value={new Date(props.snapshot.commit_date * 1000).toUTCString()} />

                    <Label>SHA</Label>
                    <Input disabled value={props.snapshot.commit_sha} />

                    <Label>Detected Files</Label>
                    <ScrollArea className="h-32 w-full rounded-md border">
                        <div className="p-4">
                            {props.snapshot.includes.map((f) => (
                                <>
                                    <div key={f} className="text-sm">
                                        {f.replace(/^\.\//, '')}
                                    </div>
                                    <Separator className="my-2" />
                                </>
                            ))}
                        </div>
                    </ScrollArea>
                </div>
            </fieldset>

            <fieldset className='grid gap-6 rounded-lg border p-4'>
                <legend className='-ml-1 px-1 text-sm font-medium'>
                    Compilation Status
                </legend>

                <div className='flex flex-col gap-10'>

                    {jobs.map((job, index) => (
                        <div key={index} className='snapshot-job-status'>
                            <div key={`line-${index}`} className='snapshot-job-status-connector'></div>

                            <div className={getStatusIndicatorClass(job.name)}></div>
                            <Label className='text-sm'>{job.name}</Label>
                        </div>
                    ))}

                </div>
            </fieldset>

            {props.snapshot.error &&
                <fieldset className='grid gap-6 rounded-lg border p-4'>
                    <legend className='-ml-1 px-1 text-sm font-medium'>
                        Error
                    </legend>
                </fieldset>
            }

        </form>

        <div className='flex flex-col gap-2 p-4'>

            <AlertDialog>
                <AlertDialogTrigger asChild>
                    <Button variant='destructive' className='w-full'>
                        <Trash className='w-4 h-4 m-1' />
                        Reset Snapshot
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone and will reset the snapshot to its initial state.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={resetSnapshot.bind(this)}>Continue</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>


            <Button variant='default' className='w-full' onClick={compileSnapshot.bind(this)}>
                <BugPlay className='w-4 h-4 m-1' />
                Render Snapshot
            </Button>
        </div>

    </div>;
};
