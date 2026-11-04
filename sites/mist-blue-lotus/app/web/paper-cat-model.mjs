// One point per real paper, sampled along a seated kitten outline and facial features.
export const CAT_PATHS=[
 [[210,180],[198,66],[270,106],[320,96],[370,106],[442,66],[430,180],[454,218],[446,260],[413,290],[385,302],[403,354],[424,413],[410,441],[353,443],[320,425],[287,443],[230,441],[216,413],[237,354],[255,302],[227,290],[194,260],[186,218],[210,180]],
 [[418,412],[465,392],[492,359],[497,322],[485,302],[472,312],[477,340],[457,363],[410,381]],
 [[247,214],[253,204],[266,204],[273,214],[267,223],[254,223],[247,214]],
 [[367,214],[373,204],[386,204],[393,214],[387,223],[374,223],[367,214]],
 [[310,243],[330,243],[320,252],[310,243]],
 [[320,252],[320,264],[308,272],[296,269]],[[320,264],[332,272],[344,269]],
 [[266,248],[207,237]],[[264,259],[198,259]],[[269,270],[208,284]],
 [[374,248],[433,237]],[[376,259],[442,259]],[[371,270],[432,284]],
 [[277,355],[278,405],[287,443]],[[363,355],[362,405],[353,443]]
];
export function catPaperPoints(papers){const paths=CAT_PATHS.map(path=>{const segments=path.slice(1).map((p,i)=>({a:path[i],b:p,length:Math.hypot(p[0]-path[i][0],p[1]-path[i][1])}));return {segments,length:segments.reduce((n,s)=>n+s.length,0)};}),total=paths.reduce((n,p)=>n+p.length,0);return papers.map((paper,i)=>{let at=(i+.5)/papers.length*total;for(const path of paths){if(at>path.length){at-=path.length;continue;}for(const s of path.segments){if(at>s.length){at-=s.length;continue;}const t=at/s.length;return {paper,x:s.a[0]+(s.b[0]-s.a[0])*t,y:s.a[1]+(s.b[1]-s.a[1])*t};}}throw Error('小猫节点定位失败');});}
