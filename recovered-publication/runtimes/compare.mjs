export function equal(a,b){
  if(typeof a==='number'&&typeof b==='number')return Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=1e-8*Math.max(1,Math.abs(b));
  if(a===b)return true;
  if(Array.isArray(a)&&Array.isArray(b))return a.length===b.length&&a.every((v,i)=>equal(v,b[i]));
  if(a&&b&&typeof a==='object'&&typeof b==='object'){const ak=Object.keys(a).sort(),bk=Object.keys(b).sort();return equal(ak,bk)&&ak.every(k=>equal(a[k],b[k]));}
  return false;
}
export function report(checks,actual){return checks.map((check,i)=>({label:check.label,input:check.args??'SQL dataset',expected:check.expected,actual:actual[i]?.__wcError?null:actual[i],error:actual[i]?.__wcError??null,passed:!actual[i]?.__wcError&&equal(actual[i],check.expected)}));}
