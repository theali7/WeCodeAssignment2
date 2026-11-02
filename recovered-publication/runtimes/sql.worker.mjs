import {PGlite,types} from './postgres/lib/index.js';
import {report} from './compare.mjs';
let database;
export async function execute({code,checks},progress=()=>{}){
  if(!database){
    progress('Loading PostgreSQL…');const base=new URL('./postgres/',import.meta.url);
    const [wasm,initdb,bundle]=await Promise.all([fetch(new URL('pglite.wasm',base)).then(r=>r.arrayBuffer()),fetch(new URL('initdb.wasm',base)).then(r=>r.arrayBuffer()),fetch(new URL('pglite.data',base)).then(r=>r.blob())]);
    database=await PGlite.create({pgliteWasmModule:await WebAssembly.compile(wasm),initdbWasmModule:await WebAssembly.compile(initdb),fsBundle:bundle,parsers:{[types.NUMERIC]:Number,[types.INT8]:Number}});
  }
  progress('Running queries…');const actual=[];let runtimeMs=0;
  for(const check of checks){
    try{
      await database.exec('ROLLBACK; DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; SET search_path TO public; SET statement_timeout TO 3000;');
      await database.exec(check.schema);
      await database.exec('BEGIN READ ONLY;');
      const started=performance.now();
      let result;
      try{result=await database.query(code,[],{rowMode:'array'});}
      finally{runtimeMs+=performance.now()-started;}
      if(!result.fields?.length)throw new Error('Return a result table with a single SELECT query.');
      if(result.rows.length>10000)throw new Error('Result limit exceeded (10,000 rows).');
      actual.push({columns:result.fields.map(f=>f.name),rows:result.rows});
    }catch(error){actual.push({__wcError:String(error.message||error)});}
    finally{await database.exec('ROLLBACK;');}
  }
  return {results:report(checks,actual),stdout:'',metrics:{runtimeMs,memoryBytes:null,memoryLabel:'Memory',note:'Sum of query wall times across datasets, including result transfer. Excludes database loading and dataset setup. Per-query peak memory is not exposed by this browser runtime.'}};
}
if(typeof self!=='undefined')self.onmessage=async e=>{try{const value=await execute(e.data,message=>self.postMessage({type:'status',message}));self.postMessage({type:'result',...value});}catch(error){self.postMessage({type:'error',message:String(error.message||error)});}};
