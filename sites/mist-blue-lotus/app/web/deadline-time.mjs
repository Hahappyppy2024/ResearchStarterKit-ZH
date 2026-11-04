export function deadlineState(at,now=Date.now()){
 if(!at)return {status:'pending',label:'待官网确认'};
 const remaining=Date.parse(at)-now;if(!Number.isFinite(remaining))return {status:'pending',label:'待官网确认'};
 if(remaining<=0)return {status:'closed',label:'已截止'};
 const days=Math.floor(remaining/86400000),hours=Math.floor(remaining%86400000/3600000),minutes=Math.floor(remaining%3600000/60000);
 return {status:'open',days,hours,label:days?`剩余 ${days} 天 ${hours} 小时`:hours?`剩余 ${hours} 小时 ${minutes} 分钟`:`剩余 ${Math.max(1,minutes)} 分钟`};
}
