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

export interface SnapshotInfoProps {
    project: TimelapseProject,
    snapshot: TimelapseSnapshot
}

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

                    <Label>Status</Label>
                    <pre><code>{ JSON.stringify(props.snapshot.status, null, 2) }</code></pre>

                    <Label>Includes</Label>
                    <pre><code>{ JSON.stringify(props.snapshot.includes, null, 2) }</code></pre>

                    <Label>Changed Pages</Label>
                    <pre><code>{ JSON.stringify(props.snapshot, null, 2) }</code></pre>
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
