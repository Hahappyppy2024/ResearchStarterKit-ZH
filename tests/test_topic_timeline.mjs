import test from 'node:test';
import assert from 'node:assert/strict';
import {categoriesForTopic,timelineEntries} from '../sites/mist-blue-lotus/app/web/topic-timeline-model.mjs';
test('Topic descendants and inherited memberships retain shared canonical categories',()=>{
 const nodes=[{id:'a',kind:'topic'},{id:'b',kind:'topic',parentId:'a'},{id:'p',kind:'problem',topicIds:['b']},{id:'child',kind:'problem',parentId:'p'},{id:'other',kind:'problem',topicIds:['else']},{id:'s',kind:'solution',topicIds:['a']}];
 assert.deepEqual(categoriesForTopic(nodes,'a','problem').map(n=>n.id),['p','child']);
 assert.deepEqual(categoriesForTopic(nodes,'a','solution').map(n=>n.id),['s']);
});
test('Paper chronology deduplicates across categories, preserves actual precision, puts unknown dates last',()=>{
 const entries=timelineEntries([{category:{id:'p'},papers:[{id:'late',title:'Late',published:'2025-02-03T12:00:00Z'},{id:'early',title:'Early',year:2017},{id:'unknown',title:'Unknown'}]},{category:{id:'s'},papers:[{id:'early',title:'Early',year:2017}]}]);
 assert.deepEqual(entries.map(p=>p.id),['early','late','unknown']);assert.equal(entries[0].time,'2017');assert.equal(entries[0].categories.length,2);assert.equal(entries[1].time,'2025-02-03');assert.equal(entries[2].time,'');
});
