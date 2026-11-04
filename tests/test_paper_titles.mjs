import {test} from 'node:test';
import assert from 'node:assert/strict';
import {titleParts,titleLabel} from '../sites/mist-blue-lotus/app/web/paper-title-model.mjs';
test('English source remains unchanged',()=>{assert.deepEqual(titleParts({title:'An English Paper'}),{title:'An English Paper',titleEn:'An English Paper',titleZh:''});});
test('Chinese source is recognized and paired metadata wins',()=>{assert.equal(titleParts({title:'中文论文'}).titleZh,'中文论文');assert.equal(titleLabel({title:'Original',titleZh:'中文译名'}),'中文译名 / Original');});
test('missing translation is labelled without inventing text',()=>{assert.equal(titleLabel({title:'Original'}),'中文译名待生成 / Original');});
