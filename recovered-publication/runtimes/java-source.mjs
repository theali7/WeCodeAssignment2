function literal(value,type){
  if(value===null)return 'null';
  if(type.endsWith('[]'))return 'new '+type+'{'+value.map(v=>literal(v,type.slice(0,-2))).join(',')+'}';
  if(type==='String')return JSON.stringify(value);
  if(type==='boolean')return value?'true':'false';
  if(type==='int')return String(value);
  throw new Error('Unsupported Java argument type: '+type);
}
export function mainSource(checks,types){
  const calls=checks.map((check,i)=>`try { results[${i}] = Solution.solve(${check.args.map((a,j)=>literal(a,types[j])).join(',')}); } catch (Throwable ex) { results[${i}] = new Failure(ex.toString()); }`).join('\n');
  return `import java.util.*;

public class Main {
  static class Failure { String message; Failure(String message) { this.message=message; } }
  static String quote(String s) {
    StringBuilder b=new StringBuilder(); b.append('"');
    for(int i=0;i<s.length();i++){char c=s.charAt(i);
      if(c=='"'||c=='\\\\'){b.append('\\\\');b.append(c);}
      else if(c=='\\n')b.append("\\\\n");
      else if(c=='\\r')b.append("\\\\r");
      else if(c=='\\t')b.append("\\\\t");
      else if(c<32){String hex=Integer.toHexString(c);b.append("\\\\u");for(int k=hex.length();k<4;k++)b.append('0');b.append(hex);}
      else b.append(c);
    }
    b.append('"');return b.toString();
  }
  static String json(Object value) {
    if(value==null)return "null";
    if(value instanceof Failure)return "{\\"__wcError\\":"+quote(((Failure)value).message)+"}";
    if(value instanceof String||value instanceof Character)return quote(value.toString());
    if(value instanceof Number||value instanceof Boolean)return value.toString();
    StringBuilder b=new StringBuilder("[");boolean first=true;
    if(value instanceof int[]){for(int item:(int[])value){if(!first)b.append(',');first=false;b.append(item);}}
    else if(value instanceof long[]){for(long item:(long[])value){if(!first)b.append(',');first=false;b.append(item);}}
    else if(value instanceof boolean[]){for(boolean item:(boolean[])value){if(!first)b.append(',');first=false;b.append(item);}}
    else if(value instanceof Object[]){for(Object item:(Object[])value){if(!first)b.append(',');first=false;b.append(json(item));}}
    else if(value instanceof Iterable){for(Object item:(Iterable<?>)value){if(!first)b.append(',');first=false;b.append(json(item));}}
    else throw new IllegalArgumentException("Return a number, boolean, string, null, array or list.");
    return b.append(']').toString();
  }
  public static void main(String[] args) {
    Object[] results=new Object[${checks.length}];
    ${calls}
    System.out.println("__WECODE_RESULT__"+json(results));
  }
}`;
}
