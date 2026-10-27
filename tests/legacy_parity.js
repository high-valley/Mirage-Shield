const fs=require('fs'),vm=require('vm');
const script=fs.readFileSync('experiments/legacy-v1.2.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const elements={},context={document:{getElementById(id){return elements[id]??={value:id==='targetBias'?'uniform':id==='strategy'?'adaptive':'learning'};}}};
vm.createContext(context);vm.runInContext(script,context);
const rows=JSON.parse(fs.readFileSync(process.argv[2]||'/tmp/mirage-parity.json','utf8'));
for(const row of rows){
 const {bias,linked,agent,policy,seed,result:b}=row;elements.targetBias.value=bias;
 const a=vm.runInContext(`run('${policy}','${agent}',makeScenario(${seed},${linked}),true)`,context);
 for(const k of ['success','decoys','moves','turns'])if(a[k]!==b[k])throw Error(JSON.stringify({bias,linked,agent,policy,seed,k}));
 a.steps.forEach((s,j)=>{for(const k of ['entry','decoy','feedback'])if(s[k]!==b.steps[j][k])throw Error('trace mismatch');});
}
console.log(`Legacy JS/Python parity: ${rows.length} episodes passed`);
