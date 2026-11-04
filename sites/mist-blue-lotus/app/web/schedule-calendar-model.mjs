export function calendarMonth(month){
 if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))throw Error('月份无效');
 const first=new Date(month+'-01T12:00:00Z'),offset=(first.getUTCDay()+6)%7;
 return Array.from({length:42},(_,i)=>{const d=new Date(first);d.setUTCDate(1-offset+i);const date=d.toISOString().slice(0,10);return {date,day:d.getUTCDate(),inMonth:date.startsWith(month)};});
}
export function moveMonth(month,delta){const d=new Date(month+'-01T12:00:00Z');d.setUTCMonth(d.getUTCMonth()+delta);return d.toISOString().slice(0,7);}
