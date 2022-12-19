# tex-history-visualizer

Run in docker:
```
 ocker run -v ${PWD}/YOUR_SOURCe:/visualizer/source -v ${PWD}/tmp:/visualizer/tmp -v ${PWD}/output:/visualizer/output tex-history-visualizer source/YOUR_MAIN.tex --test-run
```