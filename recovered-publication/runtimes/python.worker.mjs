import {loadPyodide} from './python/pyodide.mjs';
import {report} from './compare.mjs';
let runtime;
export async function execute({code,checks},progress=()=>{}){
  if(!runtime){progress('Loading Python…');const base=new URL('./python/',import.meta.url);runtime=await loadPyodide({indexURL:base.protocol==='file:'?base.pathname:base.href});}
  progress('Running tests…');
  runtime.globals.set('__wc_code',code);runtime.globals.set('__wc_checks',JSON.stringify(checks));
  const value=await runtime.runPythonAsync(`
import json as __json, io as __io, contextlib as __context, traceback as __traceback, time as __time
try:
    import tracemalloc as __trace
    __trace.stop()
    __trace.start()
    __memory_available = True
except (ImportError, RuntimeError):
    __memory_available = False
__wc_ms = 0.0
__wc_peak = 0
class __LimitedOutput(__io.StringIO):
    def write(self, value):
        if self.tell() + len(value) > 50000:
            raise RuntimeError('Output limit exceeded (50,000 characters).')
        return super().write(value)
__wc_values = []
__wc_logs = []
for __case in __json.loads(__wc_checks):
    __scope = {'__name__': '__solution__'}
    __stream = __LimitedOutput()
    try:
        with __context.redirect_stdout(__stream), __context.redirect_stderr(__stream):
            exec(compile(__wc_code, 'solution.py', 'exec'), __scope)
            if not callable(__scope.get('solve')):
                raise ValueError('Define a function named solve with the parameters in the starter code.')
            if __memory_available:
                __trace.reset_peak()
                __baseline = __trace.get_traced_memory()[0]
            __started = __time.perf_counter()
            try:
                __value = __scope['solve'](*__case['args'])
            finally:
                __wc_ms += (__time.perf_counter() - __started) * 1000
                if __memory_available:
                    __wc_peak = max(__wc_peak, max(0, __trace.get_traced_memory()[1] - __baseline))
            __json.dumps(__value, allow_nan=False)
        __wc_values.append(__value)
    except BaseException:
        __wc_values.append({'__wcError': __traceback.format_exc(limit=5)})
    __wc_logs.append(__stream.getvalue())
if __memory_available:
    __trace.stop()
__json.dumps({'values':__wc_values,'logs':__wc_logs,'runtimeMs':__wc_ms,'memoryBytes':__wc_peak if __memory_available else None}, allow_nan=False)
`);
  const parsed=JSON.parse(value);return {results:report(checks,parsed.values),stdout:parsed.logs.join('\n').slice(0,50000),metrics:{runtimeMs:parsed.runtimeMs,memoryBytes:parsed.memoryBytes,memoryLabel:'Python allocation peak',note:'Sum of solve() calls across all cases. Memory is the largest traced allocation increase during one call, excluding inputs and interpreter. Tracing adds overhead; these are local practice measurements.'}};
}
if(typeof self!=='undefined')self.onmessage=async e=>{try{const value=await execute(e.data,message=>self.postMessage({type:'status',message}));self.postMessage({type:'result',...value});}catch(error){self.postMessage({type:'error',message:String(error.message||error)});}};
