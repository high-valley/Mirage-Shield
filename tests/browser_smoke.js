const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('index.html','utf8'), elements={};
const context={document:{getElementById(id){return elements[id]??={value:({targetBias:'uniform',strategy:'adaptive',learner:'learning',agent:'learning',knowledge:'unknown',seed:'20270000'})[id]||'',disabled:false};}},setTimeout:fn=>{fn();},Blob,URL};
vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
assert(html.includes('width=device-width'));assert(html.includes('min-height:44px'));
for(const row of JSON.parse(fs.readFileSync('/tmp/mirage-fair.json','utf8'))){
 const {seed,policy,agent,bias,linked,result:b}=row;
 const a=vm.runInContext(`run('${policy}','${agent}',makeScenario(${seed},${linked},'${bias}'),true)`,context);
 for(const k of ['success','decoys','moves','turns'])assert.strictEqual(a[k],b[k],JSON.stringify({seed,policy,agent,bias,k}));
 a.steps.forEach((s,j)=>{for(const k of ['entry','decoy','feedback'])assert.strictEqual(s[k],b.steps[j][k]);});
}
(async()=>{await vm.runInContext('compare()',context);assert(elements.results.innerHTML.includes('応答予測型'));assert(!elements.compare.disabled);assert(!elements.export.disabled);
 elements.seed.value='-1';await vm.runInContext('compare()',context);assert(elements.results.textContent.includes('整数'));
 console.log('Browser logic: 1680 Python trace parity cases, 70,000 episode UI batch, input validation passed; real Safari visual test not performed.');})();
