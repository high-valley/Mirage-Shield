const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2]||'research-v2.html','utf8');
const raw=fs.readFileSync(process.argv[3]||'experiments/results_v2/holdout.json','utf8');
const embedded=html.match(/<script id="research-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
assert.deepStrictEqual(JSON.parse(embedded).rows,JSON.parse(raw).rows);
const scripts=[...html.matchAll(/<script(?:[^>]*)>([\s\S]*?)<\/script>/g)];
const elements={};
function el(){return {value:'',textContent:'',innerHTML:'',children:[],appendChild(o){this.children.push(o);if(!this.value)this.value=o.value;},click(){this.clicked=true;}};}
const created=[];
const context={document:{getElementById(id){if(!elements[id])elements[id]=el();return elements[id];},createElement(){const e=el();created.push(e);return e;}},setTimeout:fn=>fn(),Blob,URL:{createObjectURL:()=> 'blob:local-test',revokeObjectURL:()=>{}}};
context.document.getElementById('research-data').textContent=embedded;
vm.createContext(context);vm.runInContext(scripts[1][1],context);
assert.strictEqual(elements.condition.children.length,6);assert.strictEqual(elements.agent.children.length,6);
for(const condition of elements.condition.children)for(const agent of elements.agent.children){
 elements.condition.value=condition.value;elements.agent.value=agent.value;elements.condition.onchange();
 const rows=JSON.parse(raw).rows.filter(r=>r.condition===condition.value&&r.agent===agent.value);
 const candidate=rows.find(r=>r.policy==='robust');
 assert(elements.primary.innerHTML.includes((candidate.reach_rate*100).toFixed(2)+'%'));
 assert.strictEqual((elements.policies.innerHTML.match(/<article>/g)||[]).length,11);
 assert(elements.details.textContent.includes('10,000'));
 assert(elements.comparison.textContent.includes((candidate.delta_anchor*100).toFixed(2)));
 if(candidate.delta_anchor>0)assert(elements.policies.innerHTML.includes('class="bad"'));
}
elements.save.onclick();assert(created.some(e=>e.clicked&&e.download===(process.argv[2]?'mirage-sensor-audit.json':'mirage-research-v2.json')));
assert(html.includes('min-height:44px'));assert(html.includes('width=device-width'));
assert(html.includes('実機での操作確認は未実施'));
console.log('Research dashboard: all 36 filters, 396 embedded result rows, download logic and adverse values passed. Real Safari rendering not tested.');
