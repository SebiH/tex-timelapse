import {
    Bird,
    Rabbit,
    Turtle,
} from 'lucide-react';

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
import { useState } from 'react';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';

export const TimelapseSettings = () => {
    const [ compiler, setCompiler ] = useState('pdflatex');
    const [ cropTwoPage, setCropTwoPage ] = useState(false);


    return <form className='grid w-full items-start gap-6'>
        <fieldset className='grid gap-6 rounded-lg border p-4'>

            <div className='grid gap-3'>
                <Label>Compiler</Label>
                <Select value={compiler} onValueChange={setCompiler.bind(this)}>
                    <SelectTrigger id='compiler' className='items-start [&_[data-description]]:hidden'>
                        <SelectValue placeholder='Select a compiler' />
                    </SelectTrigger>
                    <SelectContent>

                        <SelectItem value='pdflatex'>
                            <div className='flex items-start gap-3 text-muted-foreground'>
                                <Rabbit className='size-5' />
                                <div className='grid gap-0.5'>
                                    <p>
                                        <span className='font-medium text-foreground'>
                                            PDF LaTeX
                                        </span>
                                        { ' ' } (Default)
                                    </p>
                                    <p className='text-xs' data-description>
                                        Used for most academic paper templates.
                                    </p>
                                </div>
                            </div>
                        </SelectItem>

                        <SelectItem value='lualatex'>
                            <div className='flex items-start gap-3 text-muted-foreground'>
                                <Bird className='size-5' />
                                <div className='grid gap-0.5'>
                                    <p>
                                        <span className='font-medium text-foreground'>
                                            LuaLaTeX
                                        </span>
                                    </p>
                                    <p className='text-xs' data-description>
                                        Description goes here.
                                    </p>
                                </div>
                            </div>
                        </SelectItem>

                        <SelectItem value='xetex'>
                            <div className='flex items-start gap-3 text-muted-foreground'>
                                <Turtle className='size-5' />
                                <div className='grid gap-0.5'>
                                    <p>
                                        <span className='font-medium text-foreground'>
                                            XeteX
                                        </span>
                                    </p>
                                    <p className='text-xs' data-description>
                                        Description goes here.
                                    </p>
                                </div>
                            </div>
                        </SelectItem>

                        <SelectItem value='custom'>
                            <div className='flex items-start gap-3 text-muted-foreground'>
                                <Turtle className='size-5' />
                                <div className='grid gap-0.5'>
                                    <p>
                                        <span className='font-medium text-foreground'>
                                            Custom
                                        </span>
                                        { ' ' } (Advanced)
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
                    <Textarea id='custom-compiler' placeholder='latexmk -pdflua -interaction=nonstopmode -synctex=1 -f' />
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
                    <Input type='number' placeholder='3' />
                </div>
                <div className='grid gap-3'>
                    <Label>Columns</Label>
                    <Input type='number' placeholder='4' />
                </div>
            </div>

            <div className='grid grid-cols-2 gap-4'>
                <div className='grid gap-3'>
                    <Label>Video Framerate</Label>
                    <Input type='number' placeholder='3' />
                </div>
                <div className='grid gap-3'>
                    <Label>Estimated Duration</Label>
                    <Input value='4:50' disabled />
                </div>
            </div>

        </fieldset>

        <fieldset className='grid gap-6 rounded-lg border p-4'>
            <legend className='-ml-1 px-1 text-sm font-medium'>
                Image Settings
            </legend>

            <div className='grid gap-3'>
                <div className="flex items-center space-x-2">
                    <Switch/>
                    <Label>Highlight Changes</Label>
                </div>
            </div>

            <div className='grid gap-3'>
                <Label>Blur</Label>
                <Slider min={0} max={10} step={1} />
            </div>

            <Separator />

            <div className='grid gap-3'>
                <Label>Crop Images</Label>
                <div className="flex items-center space-x-2">
                    <Switch checked={cropTwoPage} onCheckedChange={setCropTwoPage.bind(this)} />
                    <Label>Two-Page Cropping</Label>
                </div>
            </div>


            <div className='grid grid-cols-2 gap-4'>
                <div className='grid gap-3'>
                    <Label>Crop Top { cropTwoPage && '(even)' }</Label>
                    <Input type='number' placeholder='3' />
                </div>
                <div className='grid gap-3'>
                    <Label>Crop Bottom { cropTwoPage && '(even)' }</Label>
                    <Input type='number' placeholder='4' />
                </div>
            </div>

            <div className='grid grid-cols-2 gap-4'>
                <div className='grid gap-3'>
                    <Label>Crop Left { cropTwoPage && '(even)' }</Label>
                    <Input type='number' placeholder='3' />
                </div>
                <div className='grid gap-3'>
                    <Label>Crop Right { cropTwoPage && '(even)' }</Label>
                    <Input type='number' placeholder='4' />
                </div>
            </div>

            {cropTwoPage && <>
                <div className='grid grid-cols-2 gap-4'>
                    <div className='grid gap-3'>
                        <Label>Crop Top (odd)</Label>
                        <Input type='number' placeholder='3' />
                    </div>
                    <div className='grid gap-3'>
                        <Label>Crop Bottom (odd)</Label>
                        <Input type='number' placeholder='4' />
                    </div>
                </div>

                <div className='grid grid-cols-2 gap-4'>
                    <div className='grid gap-3'>
                        <Label>Crop Left (odd)</Label>
                        <Input type='number' placeholder='3' />
                    </div>
                    <div className='grid gap-3'>
                        <Label>Crop Right (odd)</Label>
                        <Input type='number' placeholder='4' />
                    </div>
                </div>
            </>}

        </fieldset>
    </form>;
};
