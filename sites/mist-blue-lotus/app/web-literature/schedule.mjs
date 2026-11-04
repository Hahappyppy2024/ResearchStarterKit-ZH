export const schedule = [
  {id:"practice",start:360,end:420,title:"起床 · 念经",detail:"06:00 起床，静心念经，开启新的一天。",type:"life",alert:true},
  {id:"morning",start:420,end:480,title:"喂猫 · 早餐 · 小红书论文号",detail:"照顾猫咪、吃早餐，浏览关注的论文账号。",type:"life",alert:true},
  {id:"papers",start:480,end:660,title:"阅读最新论文",detail:"Agent · Object Detection · Agent OS · Agent Security · Agent Harness（见上方论文清单）",type:"research",alert:true},
  {id:"buffer",start:660,end:720,title:"休息与机动",detail:"暂留空档：活动一下、处理临时事务。",type:"rest",alert:false},
  {id:"lunch",start:720,end:810,title:"午饭与午休",detail:"吃饭、休息，为下午留一点精力。",type:"rest",alert:true},
  {id:"slides",start:810,end:960,title:"PhD Defence · 制作答辩 slides",detail:"打磨叙事、整理证据与图表，推进答辩准备。",type:"defence",alert:true},
  {id:"directions",start:960,end:1080,title:"整理深度之眼的论文方向",detail:"梳理研究主题、归纳论文脉络，记录值得深入的方向。",type:"research",alert:true},
  {id:"detection",start:1080,end:1380,title:"Object Detection 论文",detail:"目标检测论文阅读与研究；时段内自行安排晚饭和短休息。",type:"research",alert:true},
];
export const reminders = [...schedule.filter(s=>s.alert),{id:"sleep",start:1380,end:1385,title:"结束研究，准备休息",detail:"保存今天的笔记，为明早六点起床做准备。",alert:true}];
export const timeLabel = m => `${String(Math.floor(m/60)).padStart(2,"0")}:${String(m%60).padStart(2,"0")}`;
export function chinaTime(now=new Date()){
  const p=Object.fromEntries(new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"}).formatToParts(now).map(x=>[x.type,x.value]));
  return {date:`${p.year}-${p.month}-${p.day}`,minute:Number(p.hour)*60+Number(p.minute),clock:`${p.hour}:${p.minute}:${p.second}`};
}
export function currentAt(minute){
  return schedule.find(s=>minute>=s.start&&minute<s.end)??null;
}
export function nextAt(minute){return [...schedule,{id:"sleep",start:1380,end:360,title:"结束研究，准备休息"}].find(s=>s.start>minute)??schedule[0]}
export function shiftDate(date,delta){
  const d=new Date(`${date}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+delta);return d.toISOString().slice(0,10);
}
const escapeICS = s => s.replace(/\\/g,"\\\\").replace(/\n/g,"\\n").replace(/,/g,"\\,").replace(/;/g,"\\;");
export function calendarText(date){
  const dt=m=>`${date.replaceAll("-","")}T${timeLabel(m).replace(":","")}00`;
  const lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Daily Practice//Research Schedule//ZH","CALSCALE:GREGORIAN","METHOD:PUBLISH","X-WR-CALNAME:每日修行与研究","X-WR-TIMEZONE:Asia/Shanghai",
    "BEGIN:VTIMEZONE","TZID:Asia/Shanghai","BEGIN:STANDARD","DTSTART:19700101T000000","TZOFFSETFROM:+0800","TZOFFSETTO:+0800","TZNAME:CST","END:STANDARD","END:VTIMEZONE"];
  for(const task of reminders) lines.push("BEGIN:VEVENT",`UID:daily-practice-${task.id}@research-schedule`,`DTSTAMP:${new Date().toISOString().replace(/[-:]/g,"").replace(/\.\d{3}/,"")}`,`DTSTART;TZID=Asia/Shanghai:${dt(task.start)}`,`DTEND;TZID=Asia/Shanghai:${dt(task.end)}`,"RRULE:FREQ=DAILY",`SUMMARY:${escapeICS(task.title)}`,`DESCRIPTION:${escapeICS(task.detail)}`,"BEGIN:VALARM","TRIGGER:PT0M","ACTION:DISPLAY",`DESCRIPTION:${escapeICS(task.title)}`,"END:VALARM","END:VEVENT");
  lines.push("END:VCALENDAR");
  // Fold UTF-8 lines without splitting a multibyte character (RFC 5545).
  return lines.map(line=>{let out="",count=0;for(const char of line){const n=new TextEncoder().encode(char).length;if(count+n>73){out+="\r\n ";count=1;}out+=char;count+=n;}return out}).join("\r\n")+"\r\n";
}
