## Issues

#### For a resource `arn:aws:states:::states:startExecution.sync:2` the mock data is different from the actual state.

```
# Mock
Output: string
StopDate: string
StartDate: string
Output: string

# Actual
Output: object
StopDate: int
StartDate: int
Output: object
```

I also had to change the step functiondefinition:

`"Output": "{% $merge([$states.result.Output, $states.input, {'h5ad_file':$states.result.Output.in_file}])  %}"`

Was changed to:

`"Output": "{% $merge([$parse($states.result.Output), $states.input, {'h5ad_file':$parse($states.result.Output).in_file}])  %}"`
