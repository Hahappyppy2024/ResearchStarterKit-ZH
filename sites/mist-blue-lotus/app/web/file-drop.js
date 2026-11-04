/* Reusable native file picker and drag/drop surface. File bytes stay on this server. */
export function mountFileDrop(input,onFiles,{label='拖入文件，或点击选择文件',accept=null,multiple=true,status=null}={}){
 const box=document.createElement('section');box.className='local-file-drop';box.tabIndex=0;box.setAttribute('role','group');box.setAttribute('aria-label',label);
 const title=document.createElement('p');title.textContent=label;box.append(title);input.before(box);box.append(input);input.multiple=multiple;
 if(accept)input.accept=accept;
 async function deliver(files){if(!files.length)return;const list=[...files];if(!multiple&&list.length>1){if(status)status.textContent='每次请选择一个 PDF 文件';return;}await onFiles(list);}
 input.onchange=()=>deliver(input.files);box.onkeydown=e=>{if(e.target===box&&(e.key==='Enter'||e.key===' ')){e.preventDefault();input.click()}};
 for(const event of ['dragenter','dragover'])box.addEventListener(event,e=>{e.preventDefault();e.stopPropagation();e.dataTransfer.dropEffect='copy';box.classList.add('drag-over')});
 box.addEventListener('dragleave',e=>{if(!box.contains(e.relatedTarget))box.classList.remove('drag-over')});
 box.addEventListener('drop',e=>{e.preventDefault();e.stopPropagation();box.classList.remove('drag-over');if(!input.disabled)deliver(e.dataTransfer.files)});
 return box;
}
