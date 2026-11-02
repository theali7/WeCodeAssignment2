import {load} from './teavm/wasm-runtime.js';
import {mainSource} from './java-source.mjs';
import {report} from './compare.mjs';
let compiler;
export async function execute({code,checks,javaTypes},progress=()=>{}){
  if(!compiler){
    progress('Loading Java compiler…');
    const base=new URL('./teavm/',import.meta.url);
    const [module,sdk,lib]=await Promise.all([fetch(new URL('compiler.wasm',base)).then(r=>r.arrayBuffer()).then(bytes=>load(new Int8Array(bytes))),fetch(new URL('compile-classlib.bin',base)).then(r=>r.arrayBuffer()),fetch(new URL('runtime-classlib.bin',base)).then(r=>r.arrayBuffer())]);
    compiler=module.exports.createCompiler();compiler.setSdk(new Int8Array(sdk));compiler.setTeaVMClasslib(new Int8Array(lib));
  }
  progress('Compiling Java…');let diagnostics=[];
  const listener=compiler.onDiagnostic(d=>{if(d.severity==='error')diagnostics.push(`${d.fileName??'Solution.java'}:${d.lineNumber??'?'} ${d.message}`);});
  try{
    compiler.clearSourceFiles();compiler.clearOutputFiles();
    compiler.addSourceFile('Solution.java',code);compiler.addSourceFile('Main.java',mainSource(checks,javaTypes));
    if(!compiler.compile())throw new Error(diagnostics.join('\n')||'Java compilation failed. Keep the class name Solution and the solve method signature.');
    if(!compiler.generateWebAssembly({outputName:'solution',mainClass:'Main'}))throw new Error(diagnostics.join('\n')||'This Java feature is not supported by the browser compiler.');
    progress('Running tests…');let output='';
    const append=c=>{if(output.length>=1000000)throw new Error('Output limit exceeded.');output+=String.fromCharCode(c);};
    const run=await load(compiler.getWebAssemblyOutputFile('solution.wasm'),{installImports(o){o.teavmConsole.putcharStdout=append;o.teavmConsole.putcharStderr=append;}});
    const started=performance.now();
    await run.exports.main([]);
    const runtimeMs=performance.now()-started;
    const marker='__WECODE_RESULT__',index=output.lastIndexOf(marker);
    if(index<0)throw new Error('The Java program exited before returning its results.');
    const values=JSON.parse(output.slice(index+marker.length).trim());
    return {results:report(checks,values),stdout:output.slice(0,index).slice(0,50000),metrics:{runtimeMs,memoryBytes:null,memoryLabel:"Memory",note:"Execution of the test harness, including input construction and output formatting. Excludes compilation and download. Java GC heap usage is not exposed by this browser runtime."}};
  }finally{listener.destroy();}
}
if(typeof self!=='undefined')self.onmessage=async e=>{try{const value=await execute(e.data,message=>self.postMessage({type:'status',message}));self.postMessage({type:'result',...value});}catch(error){self.postMessage({type:'error',message:String(error.message||error)});}};
