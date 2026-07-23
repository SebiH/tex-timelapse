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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useEffect, useState } from 'react';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { UIState } from '@/models/ui-state';
import { TimelapseProject } from '@/models/project';
import { TimelapseConfig } from '@/models/config';
import { TimelapseJob } from '@/models/job';
import { Button } from '@/components/ui/button';
import { Play, Square, Trash } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/api/client';

type TimelapseSettingsProps = {
    project: TimelapseProject;
};

const pdflatexCmd = 'latexmk -pdf -interaction=nonstopmode -synctex=1 -f';
const lualatexCmd = 'latexmk -pdflatex=\'lualatex %O %S\' -interaction=nonstopmode -pdf -synctex=1 -f';
const xetexCmd = 'latexmk -pdflatex=\'xelatex %O %S\' -interaction=nonstopmode -pdf -synctex=1 -f';

function debounce<Args extends unknown[]>(func: (...args: Args) => void, timeout = 300): (...args: Args) => void {
    let timer: ReturnType<typeof setTimeout>;
    return (...args: Args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func(...args); }, timeout);
    };
}

const sendConfig = debounce((project: TimelapseProject, config: TimelapseConfig) => {
    api.updateProjectConfig(project.name, config).catch((e) => console.error(e));
}, 1000);




export const TimelapseSettings = ({ project }: TimelapseSettingsProps) => {
    const [ config, setConfig ] = useState(project.config);
    const [ compiler, setCompiler ] = useState('pdflatex');
    const [ activeJob, setActiveJob ] = useState<TimelapseJob | null>(null);

    useEffect(() => {
        const sub = UIState.project.subscribe(p => {
            if (p) {
                setConfig(p.config);
                if (p.config.latexCmd === pdflatexCmd)
                    setCompiler('pdflatex');
                else if (p.config.latexCmd === lualatexCmd)
                    setCompiler('lualatex');
                else if (p.config.latexCmd === xetexCmd)
                    setCompiler('xetex');
                else
                    setCompiler('custom');
            }
        });
        return () => sub.unsubscribe();
    }, []);

    useEffect(() => {
        const sub = UIState.activeJob.subscribe(setActiveJob);
        return () => sub.unsubscribe();
    }, []);

    const isRendering = activeJob?.status === 'running';

    const updateConfig = <K extends keyof TimelapseConfig>(key: K, value: TimelapseConfig[K]) => {
        const newConfig = { ...config, [key]: value };
        UIState.setProject({ ...project, config: newConfig });
        sendConfig(project, newConfig);
    };

    // `e.target.valueAsNumber` is NaN when a numeric input is cleared; guard
    // it here so a cleared field doesn't push NaN into the config (and from
    // there into the debounced POST).
    const updateNumberConfig = <K extends keyof TimelapseConfig>(key: K, value: number) => {
        if (Number.isNaN(value)) return;
        updateConfig(key, value as TimelapseConfig[K]);
    };

    const setCompilerCmd = (mode: string) => {
        if (mode === 'pdflatex')
            updateConfig('latexCmd', pdflatexCmd);
        else if (mode === 'lualatex')
            updateConfig('latexCmd', lualatexCmd);
        else if (mode === 'xetex')
            updateConfig('latexCmd', xetexCmd);
        else if (mode === 'custom') {
            updateConfig('latexCmd', '');
        }
    };

    const compileProject = async () => {
        // The project name doubles as the output mp4 basename - the backend
        // slugifies/derives the file from it, so there's nothing else on
        // this form that would make a better default.
        const job = await UIState.startRender(project, project.name);
        if (job) {
            toast.success('Render started', {
                description: 'Project is being rendered',
            });
        } else {
            toast.error('Rendering error', {
                description: 'Project could not be rendered',
            });
        }
    };

    const cancelRender = async () => {
        const ok = await UIState.cancelRender();
        if (ok) {
            toast.success('Render cancelled');
        } else {
            toast.error('Error', {
                description: 'Render could not be cancelled',
            });
        }
    };

    const resetProjectSnapshots = async () => {
        try {
            await UIState.resetProjectSnapshots(project);
            toast.success('Project reset', {
                description: 'Project was reset successfully',
            });
        } catch (e) {
            toast.error('Error', {
                description: 'Project could not be reset',
            });
        }
    };


    return <div className='flex flex-col justify-between w-full h-full'>

        <form className='grid w-full items-start gap-6 overflow-y-auto'>
            <fieldset className='grid gap-6 rounded-lg border p-4'>

                <div className='grid gap-3'>
                    <Label>Compiler</Label>
                    <Select value={compiler} onValueChange={setCompilerCmd}>
                        <SelectTrigger id='compiler' className='items-start [&_[data-description]]:hidden'>
                            <SelectValue placeholder='Select a latex compiler' />
                        </SelectTrigger>
                        <SelectContent>

                            <SelectItem value='pdflatex'>
                                <div className='flex items-start gap-3 text-muted-foreground'>
                                    <div className='grid gap-0.5'>
                                        <p>
                                            <span className='font-medium text-foreground'>
                                                PDF LaTeX
                                            </span>
                                            {' '} (Default)
                                        </p>
                                        <p className='text-xs' data-description>
                                            Used for most academic paper templates.
                                        </p>
                                    </div>
                                </div>
                            </SelectItem>

                            <SelectItem value='lualatex'>
                                <div className='flex items-start gap-3 text-muted-foreground'>
                                    <div className='grid gap-0.5'>
                                        <p>
                                            <span className='font-medium text-foreground'>
                                                LuaLaTeX
                                            </span>
                                        </p>
                                        <p className='text-xs' data-description>
                                            LuaLatex compiler for modern templates.
                                        </p>
                                    </div>
                                </div>
                            </SelectItem>

                            <SelectItem value='xetex'>
                                <div className='flex items-start gap-3 text-muted-foreground'>
                                    <div className='grid gap-0.5'>
                                        <p>
                                            <span className='font-medium text-foreground'>
                                                XeteX
                                            </span>
                                        </p>
                                        <p className='text-xs' data-description>
                                            XeTeX compiler for custom projects.
                                        </p>
                                    </div>
                                </div>
                            </SelectItem>

                            <SelectItem value='custom'>
                                <div className='flex items-start gap-3 text-muted-foreground'>
                                    <div className='grid gap-0.5'>
                                        <p>
                                            <span className='font-medium text-foreground'>
                                                Custom
                                            </span>
                                            {' '} (Advanced)
                                        </p>
                                        <p className='text-xs' data-description>
                                            Specify your own command for compiling.
                                        </p>
                                    </div>
                                </div>
                            </SelectItem>
                        </SelectContent>
                    </Select>

                    {compiler === 'custom' && <div className='grid gap-3'>
                        <Label htmlFor='custom-compiler'>Custom Compiler</Label>
                        <Textarea id='custom-compiler' value={config.latexCmd}
                            onChange={e => updateConfig('latexCmd', e.target.value)}
                            placeholder='latexmk -pdf -interaction=nonstopmode -synctex=1 -f' />
                    </div>}
                </div>
            </fieldset>


            <fieldset className='grid gap-6 rounded-lg border p-4'>
                <legend className='-ml-1 px-1 text-sm font-medium'>
                    Video Settings
                </legend>


                <div className='grid grid-cols-2 gap-4'>
                    <div className='grid gap-3'>
                        <Label>Rows</Label>
                        <Input type='number' placeholder='3' value={config.rows} onChange={e => updateNumberConfig('rows', e.target.valueAsNumber)} min={1} />
                    </div>
                    <div className='grid gap-3'>
                        <Label>Columns</Label>
                        <Input type='number' placeholder='4' value={config.columns} onChange={e => updateNumberConfig('columns', e.target.valueAsNumber)} min={1} />
                    </div>
                </div>

                <div className='grid grid-cols-2 gap-4'>
                    <div className='grid gap-3'>
                        <Label>Video Framerate</Label>
                        <Input type='number' placeholder='4' value={config.framerate} onChange={e => updateNumberConfig('framerate', e.target.valueAsNumber)} min={1} />
                    </div>
                    <div className='grid gap-3'>
                        <Label>Estimated Duration</Label>
                        <Input value={new Date(project.snapshots.length / Math.max(1, config.framerate) * 1000).toISOString().slice(11, 19)} disabled />
                    </div>
                </div>

            </fieldset>

            <fieldset className='grid gap-6 rounded-lg border p-4'>
                <legend className='-ml-1 px-1 text-sm font-medium'>
                    Image Settings
                </legend>

                <div className='grid gap-3'>
                    <div className="flex items-center space-x-2">
                        <Switch checked={config.highlightChanges} onCheckedChange={v => updateConfig('highlightChanges', v)} />
                        <Label>Highlight Changes</Label>
                    </div>
                </div>

                <div className='grid gap-3'>
                    <Label>Gaussian Blur</Label>
                    <div className='flex items-center gap-3'>
                        <Slider min={0} max={20} step={0.1} value={[config.blur]} onValueChange={v => updateConfig('blur', v[0])} />
                        <Label className='text-xs'>{config.blur}</Label>
                    </div>
                </div>

                <Separator />

                <div className='grid gap-3'>
                    <div className="flex items-center space-x-2">
                        <Switch checked={config.crop} onCheckedChange={v => updateConfig('crop', v)} />
                        <Label>Crop Page Margins</Label>
                    </div>
                </div>


                {config.crop && <>
                    <div className='grid gap-3'>
                        <div className="flex items-center space-x-2">
                            <Switch checked={config.cropTwoPage} onCheckedChange={v => updateConfig('cropTwoPage', v)} />
                            <Label>Two-Page Cropping</Label>
                        </div>
                    </div>


                    <div className='grid grid-cols-2 gap-4'>
                        <div className='grid gap-3'>
                            <Label>Crop Top {config.cropTwoPage && '(even)'}</Label>
                            <Input type='number' placeholder='0' value={config.cropTop} onChange={e => updateNumberConfig('cropTop', e.target.valueAsNumber)} min={0} />
                        </div>
                        <div className='grid gap-3'>
                            <Label>Crop Bottom {config.cropTwoPage && '(even)'}</Label>
                            <Input type='number' placeholder='0' value={config.cropBottom} onChange={e => updateNumberConfig('cropBottom', e.target.valueAsNumber)} min={0} />
                        </div>
                    </div>

                    <div className='grid grid-cols-2 gap-4'>
                        <div className='grid gap-3'>
                            <Label>Crop Left {config.cropTwoPage && '(even)'}</Label>
                            <Input type='number' placeholder='0' value={config.cropLeft} onChange={e => updateNumberConfig('cropLeft', e.target.valueAsNumber)} min={0} />
                        </div>
                        <div className='grid gap-3'>
                            <Label>Crop Right {config.cropTwoPage && '(even)'}</Label>
                            <Input type='number' placeholder='0' value={config.cropRight} onChange={e => updateNumberConfig('cropRight', e.target.valueAsNumber)} min={0} />
                        </div>
                    </div>
                </>}

                {config.crop && config.cropTwoPage && <>
                    <div className='grid grid-cols-2 gap-4'>
                        <div className='grid gap-3'>
                            <Label>Crop Top (odd)</Label>
                            <Input type='number' placeholder='0' value={config.cropAltTop} onChange={e => updateNumberConfig('cropAltTop', e.target.valueAsNumber)} min={0} />
                        </div>
                        <div className='grid gap-3'>
                            <Label>Crop Bottom (odd)</Label>
                            <Input type='number' placeholder='0' value={config.cropAltBottom} onChange={e => updateNumberConfig('cropAltBottom', e.target.valueAsNumber)} min={0} />
                        </div>
                    </div>

                    <div className='grid grid-cols-2 gap-4'>
                        <div className='grid gap-3'>
                            <Label>Crop Left (odd)</Label>
                            <Input type='number' placeholder='0' value={config.cropAltLeft} onChange={e => updateNumberConfig('cropAltLeft', e.target.valueAsNumber)} min={0} />
                        </div>
                        <div className='grid gap-3'>
                            <Label>Crop Right (odd)</Label>
                            <Input type='number' placeholder='0' value={config.cropAltRight} onChange={e => updateNumberConfig('cropAltRight', e.target.valueAsNumber)} min={0} />
                        </div>
                    </div>
                </>}

            </fieldset>

        </form>

        <div className='flex flex-col gap-2 p-4'>

            <AlertDialog>
                <AlertDialogTrigger asChild>
                    <Button variant='destructive' className='w-full'>
                        <Trash className='w-4 h-4 m-1' />
                        Reset Snapshots
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone and will reset all snapshots to their initial state.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={resetProjectSnapshots}>Continue</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {isRendering && activeJob && <div className='grid gap-2'>
                <div className='flex items-center justify-between text-xs text-muted-foreground'>
                    <span>{activeJob.stage || 'Starting...'}</span>
                    <span>{Math.round(activeJob.stage_progress * 100)}%</span>
                </div>
                <Progress value={activeJob.stage_progress * 100} />
            </div>}

            {isRendering
                ? <Button variant='destructive' className='w-full' onClick={cancelRender}>
                    <Square className='w-4 h-4 m-1' />
                    Cancel
                </Button>
                : <Button variant='default' className='w-full' onClick={compileProject}>
                    <Play className='w-4 h-4 m-1' />
                    Start
                </Button>}
        </div>
    </div>;
};
