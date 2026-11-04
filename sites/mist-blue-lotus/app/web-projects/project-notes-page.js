import {mountProjectNotes} from './project-notes.js';
const id=new URLSearchParams(location.search).get('project'),root=document.getElementById('project-notes-card');
if(!id){root.textContent='请从项目顶部的“打开项目笔记”进入。';document.getElementById('export-project-notes').hidden=true;}
else{
 document.getElementById('back-project').href='/?project='+encodeURIComponent(id);
 document.getElementById('return-project').href='/?project='+encodeURIComponent(id);
 document.getElementById('export-project-notes').href='/api/export?id='+encodeURIComponent(id)+'&format=md';
 document.getElementById('export-project-notes').setAttribute('download','项目笔记.md');
 try{const response=await fetch('/api/project?id='+encodeURIComponent(id),{cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(data.error||'项目读取失败');document.getElementById('notes-project-name').textContent=data.project.name+' · 项目笔记';document.title=data.project.name+' · 项目笔记';mountProjectNotes(root,id);}catch(error){root.textContent=error.message;}
}
